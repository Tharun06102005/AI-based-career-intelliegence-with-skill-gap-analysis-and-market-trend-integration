"""Careers API router.

Provides endpoints for exploring career roles, ranking career fit for a candidate,
retrieving detailed career requirements, and comparing two career roles side by side.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import CareerMetric, CareerRole, Profile, ProfileSkill, Resume
from models.session import get_db
from schemas.career import (
    CareerCompareRequest,
    CareerCompareResponse,
    CareerComparisonItem,
    CareerDetailResponse,
    CareerPathResponse,
    CareerRankRequest,
    CareerRankResult,
    CareerResponse,
    CareerSkillItem,
)
from scoring.career_scorer import calculate_career_fit, rank_careers
from scoring.gap_engine import get_full_gap_report
from services.career_path import get_career_path, get_current_level
from services.career_seeder import CAREER_PROFILES

router = APIRouter(prefix="/api/careers", tags=["careers"])


def _load_demand_scores_cache() -> Dict[str, float]:
    """Load precomputed market demand scores from processed JSON file."""
    scores_file = PROJECT_ROOT / "data" / "processed" / "demand_scores.json"
    if scores_file.exists():
        try:
            with open(scores_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


@router.get("", response_model=List[CareerResponse], status_code=status.HTTP_200_OK)
@router.get("/", response_model=List[CareerResponse], status_code=status.HTTP_200_OK, include_in_schema=False)
def list_careers(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return list of all canonical career roles with demand scores and required skills."""
    roles = db.query(CareerRole).order_by(CareerRole.id).all()
    cached_scores = _load_demand_scores_cache()

    results: List[Dict[str, Any]] = []
    for role in roles:
        # Determine demand score
        d_score = 0.0
        if role.metrics and role.metrics.demand_score is not None:
            d_score = role.metrics.demand_score
        else:
            d_score = cached_scores.get(role.name, 0.5)

        # Determine required skills list
        if role.career_skills:
            req_skills = [
                cs.skill.canonical_name for cs in role.career_skills if cs.required
            ]
            if not req_skills:
                req_skills = [cs.skill.canonical_name for cs in role.career_skills]
        elif role.name in CAREER_PROFILES:
            req_skills = list(CAREER_PROFILES[role.name].get("required_skills", []))  # type: ignore
        else:
            req_skills = []

        results.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "demand_score": round(float(d_score), 4),
            "required_skills": req_skills,
        })

    return results


@router.post("/rank", response_model=List[CareerRankResult], status_code=status.HTTP_200_OK)
def rank_profile_careers(
    payload: CareerRankRequest,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Rank all canonical careers by CareerFit score for a given candidate profile."""
    # 1. Validate profile existence
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{payload.profile_id}' not found.",
        )

    # 2. Fetch candidate profile skills
    profile_skills_records = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == payload.profile_id)
        .join(ProfileSkill.skill)
        .all()
    )
    profile_skills = [
        {
            "skill_name": ps.skill.canonical_name,
            "confidence": ps.confidence or "Medium",
            "is_verified": getattr(ps, "is_verified", False),
            "verified_score": getattr(ps, "verified_score", None),
        }
        for ps in profile_skills_records
    ]

    # 3. Fetch resume sections for experience alignment
    resume = (
        db.query(Resume)
        .filter(Resume.profile_id == payload.profile_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    resume_sections: Dict[str, str] = {}
    if resume and resume.sections:
        resume_sections = {s.section_type: s.text or "" for s in resume.sections}
    else:
        if profile.experience_summary:
            resume_sections["experience"] = profile.experience_summary
        if profile.education_summary:
            resume_sections["education"] = profile.education_summary

    # 4. Load all career roles and demand scores
    roles = db.query(CareerRole).all()
    role_id_map = {r.name: r.id for r in roles}
    cached_scores = _load_demand_scores_cache()

    demand_scores_map: Dict[str, float] = {}
    for r in roles:
        if r.metrics and r.metrics.demand_score is not None:
            demand_scores_map[r.name] = r.metrics.demand_score
        else:
            demand_scores_map[r.name] = cached_scores.get(r.name, 0.5)

    # 5. Run scoring engine ranking
    all_career_names = [r.name for r in roles] if roles else list(CAREER_PROFILES.keys())
    ranked = rank_careers(
        profile_skills=profile_skills,
        resume_sections=resume_sections,
        all_careers=all_career_names,
        demand_scores=demand_scores_map,
    )

    # 6. Format response
    response_list: List[Dict[str, Any]] = []
    for item in ranked:
        c_name = item["career_name"]
        c_id = role_id_map.get(c_name, 0)
        d_score = demand_scores_map.get(
            c_name, item.get("components", {}).get("market_demand", 0.5)
        )

        response_list.append({
            "career_id": c_id,
            "career_name": c_name,
            "total_score": item["total_score"],
            "components": item["components"],
            "engine_version": item.get("engine_version", "score-1.0"),
            "demand_score": round(float(d_score), 4),
        })

    return response_list


@router.get("/{id}", response_model=CareerDetailResponse, status_code=status.HTTP_200_OK)
def get_career_details(id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve detailed specification of a career role including skill weights and job counts."""
    career = db.query(CareerRole).filter(CareerRole.id == id).first()
    if not career:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Career role with id {id} not found.",
        )

    # Format skills with weights
    skills_with_weights: List[Dict[str, Any]] = []
    if career.career_skills:
        for cs in career.career_skills:
            skills_with_weights.append({
                "skill_name": cs.skill.canonical_name,
                "importance": round(float(cs.importance or 1.0), 2),
                "required": cs.required,
            })
    elif career.name in CAREER_PROFILES:
        for s in CAREER_PROFILES[career.name]["required_skills"]:  # type: ignore
            skills_with_weights.append({
                "skill_name": str(s),
                "importance": 1.0,
                "required": True,
            })

    # Retrieve metrics
    cached_scores = _load_demand_scores_cache()
    if career.metrics:
        demand_score = career.metrics.demand_score or 0.0
        job_count = career.metrics.job_count or 0
    else:
        demand_score = cached_scores.get(career.name, 0.5)
        job_count = 0

    return {
        "id": career.id,
        "name": career.name,
        "description": career.description,
        "required_skills": skills_with_weights,
        "demand_score": round(float(demand_score), 4),
        "job_count": int(job_count),
    }


@router.get("/{id}/path", response_model=CareerPathResponse, status_code=status.HTTP_200_OK)
def get_career_path_endpoint(
    id: int,
    profile_id: Optional[UUID] = Query(
        None, description="Optional UUID of candidate profile to evaluate current level"
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full career progression path and evaluate candidate's current level.

    Loads career from database, retrieves candidate skills if profile_id provided,
    calls get_current_level, and returns the career path + current level metrics.
    """
    career = db.query(CareerRole).filter(CareerRole.id == id).first()
    if not career:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Career role with id {id} not found.",
        )

    # 1. Load career path
    try:
        career_path = get_career_path(career.name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # 2. Extract profile skills if profile_id is provided
    profile_skills: List[str] = []
    if profile_id:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile '{profile_id}' not found.",
            )
        profile_skills_records = (
            db.query(ProfileSkill)
            .filter(ProfileSkill.profile_id == profile_id)
            .join(ProfileSkill.skill)
            .all()
        )
        profile_skills = [ps.skill.canonical_name for ps in profile_skills_records]

    # 3. Assess candidate level
    level_assessment = get_current_level(profile_skills, career.name)

    return {
        "career_id": career.id,
        "career_name": career.name,
        "path": career_path,
        "current_level": level_assessment["current_level"],
        "current_level_match": level_assessment["current_level_match"],
        "next_level": level_assessment["next_level"],
        "skills_to_advance": level_assessment["skills_to_advance"],
        "levels_away": level_assessment["levels_away"],
    }


@router.post("/compare", response_model=CareerCompareResponse, status_code=status.HTTP_200_OK)
def compare_careers(
    payload: CareerCompareRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Compare exactly two career roles side by side for a candidate profile.

    Assesses fit score, readiness, missing skills, market demand, and effort-to-reach.
    """
    if len(payload.career_ids) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="career_ids must contain exactly 2 career IDs to compare.",
        )

    # 1. Verify candidate profile
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{payload.profile_id}' not found.",
        )

    # 2. Extract profile skills and resume sections for scoring
    profile_skills_records = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == payload.profile_id)
        .join(ProfileSkill.skill)
        .all()
    )
    profile_skills = [
        {
            "skill_name": ps.skill.canonical_name,
            "confidence": ps.confidence or "Medium",
        }
        for ps in profile_skills_records
    ]

    resume = (
        db.query(Resume)
        .filter(Resume.profile_id == payload.profile_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    resume_sections: Dict[str, str] = {}
    if resume and resume.sections:
        resume_sections = {s.section_type: s.text or "" for s in resume.sections}
    else:
        if profile.experience_summary:
            resume_sections["experience"] = profile.experience_summary
        if profile.education_summary:
            resume_sections["education"] = profile.education_summary

    cached_scores = _load_demand_scores_cache()
    comparison_items: List[Dict[str, Any]] = []

    # 3. Analyze each career
    for cid in payload.career_ids:
        career = db.query(CareerRole).filter(CareerRole.id == cid).first()
        if not career:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Career role with id {cid} not found.",
            )

        # Gap analysis
        gap_report = get_full_gap_report(
            profile_id=payload.profile_id,
            career_id=cid,
            db=db,
        )

        # Market demand
        if career.metrics and career.metrics.demand_score is not None:
            demand_val = career.metrics.demand_score
        else:
            demand_val = cached_scores.get(career.name, 0.5)

        # Fit score
        fit_result = calculate_career_fit(
            profile_skills=profile_skills,
            career=career.name,
            resume_sections=resume_sections,
            market_demand=demand_val,
        )

        # Effort to reach calculation
        missing_count = len(gap_report.get("missing_skills", []))
        if missing_count <= 2:
            effort = "Low"
        elif missing_count <= 4:
            effort = "Medium"
        else:
            effort = "High"

        comparison_items.append({
            "career_name": career.name,
            "fit_score": round(fit_result["total_score"], 2),
            "readiness": round(gap_report["readiness"], 2),
            "matched_skills": gap_report.get("matched_skills", []),
            "missing_skills": gap_report.get("missing_skills", []),
            "demand_score": round(float(demand_val), 4),
            "effort_to_reach": effort,
        })

    return {
        "profile_id": str(payload.profile_id),
        "comparisons": comparison_items,
        "careers": comparison_items,
    }

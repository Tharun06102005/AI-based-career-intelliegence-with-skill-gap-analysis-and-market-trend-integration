"""Roadmaps API router.

Provides endpoints for generating LLM-powered explanations of career fit and
actionable step-by-step learning roadmaps for missing technical skills.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import CareerRole, Profile, ProfileSkill, Resume
from models.session import get_db
from scoring.career_scorer import calculate_career_fit
from scoring.gap_engine import get_full_gap_report
from services.llm_explainer import generate_explanation, generate_roadmap

router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])


class RoadmapRequest(BaseModel):
    """Payload to generate career roadmap and explanation."""

    profile_id: UUID = Field(..., description="UUID of candidate profile")
    career_id: int = Field(..., description="ID of target career role")
    days_available: int = Field(default=30, description="Target study timeline in days (e.g. 7, 15, 30, 60, 90)")


@router.post("", status_code=status.HTTP_200_OK)
@router.post("/", status_code=status.HTTP_200_OK, include_in_schema=False)
def generate_career_roadmap(
    payload: RoadmapRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generate LLM explanation of computed scores and a learning roadmap for skill gaps.

    CRITICAL RULE:
        The LLM only explains computed results. It NEVER calculates or overrides scores.
    """
    # 1. Fetch gap report
    try:
        gap_report = get_full_gap_report(
            profile_id=payload.profile_id,
            career_id=payload.career_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # 2. Fetch career role
    career = db.query(CareerRole).filter(CareerRole.id == payload.career_id).first()
    if not career:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Career role with id {payload.career_id} not found",
        )

    # 3. Fetch profile skills & resume sections to compute CareerFit
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
        profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
        if profile:
            if profile.experience_summary:
                resume_sections["experience"] = profile.experience_summary
            if profile.education_summary:
                resume_sections["education"] = profile.education_summary

    career_fit_result = calculate_career_fit(
        profile_skills=profile_skills,
        career=career.name,
        resume_sections=resume_sections,
    )

    # 4. Generate LLM explanation and roadmap
    explanation_result = generate_explanation(
        career_fit_result=career_fit_result,
        gap_report=gap_report,
    )

    roadmap_items = generate_roadmap(
        missing_skills=gap_report.get("missing_skills", []),
        career_name=career.name,
        days_available=payload.days_available,
    )

    return {
        "career_name": career.name,
        "fit_score": career_fit_result["total_score"],
        "readiness": gap_report["readiness"],
        "explanation": explanation_result["explanation"],
        "roadmap": roadmap_items,
        "days_available": payload.days_available,
        "gap_analysis": {
            "matched_skills": gap_report["matched_skills"],
            "missing_skills": gap_report["missing_skills"],
            "partial_skills": gap_report["partial_skills"],
        },
    }

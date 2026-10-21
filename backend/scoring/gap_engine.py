"""Skill Gap and Readiness Engine.

Evaluates candidate profile skills against career role requirements to determine:
- Skill match classifications (Matched, Partially Matched, Missing, Optional)
- Weighted career readiness scores
- Prioritized skill gaps sorted by importance

CRITICAL CONSTRAINTS:
- Adding relevant skill must INCREASE readiness.
- Adding irrelevant skill must have ZERO impact.
- Removing required skill must DECREASE readiness.
- Deterministic: same inputs always produce identical results.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from uuid import UUID

from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import CareerRole, CareerSkill, Profile, ProfileSkill, Resume, Skill, SkillGap
from scoring.career_scorer import calculate_experience_alignment
from services.career_seeder import CAREER_PROFILES
from services.skill_normalizer import normalize_skill


def _parse_skill_input(skill_item: Any) -> Tuple[str, float, bool]:
    """Extract (skill_name, importance, required) from various skill representations."""
    skill_name = ""
    importance = 1.0
    required = True

    if isinstance(skill_item, str):
        skill_name = skill_item
    elif isinstance(skill_item, dict):
        skill_name = (
            skill_item.get("skill_name")
            or skill_item.get("skill")
            or skill_item.get("name")
            or skill_item.get("canonical_name")
            or ""
        )
        importance = float(skill_item.get("importance", 1.0) or 1.0)
        required = bool(skill_item.get("required", True))
    elif hasattr(skill_item, "skill") and hasattr(skill_item.skill, "canonical_name"):
        skill_name = skill_item.skill.canonical_name
        importance = float(getattr(skill_item, "importance", 1.0) or 1.0)
        required = bool(getattr(skill_item, "required", True))
    elif hasattr(skill_item, "canonical_name"):
        skill_name = skill_item.canonical_name
        importance = float(getattr(skill_item, "importance", 1.0) or 1.0)
        required = bool(getattr(skill_item, "required", True))
    elif hasattr(skill_item, "skill_name"):
        skill_name = skill_item.skill_name
        importance = float(getattr(skill_item, "importance", 1.0) or 1.0)
        required = bool(getattr(skill_item, "required", True))

    return skill_name.strip(), importance, required


def _find_profile_match(
    target_skill_name: str,
    profile_skills: Sequence[Any],
) -> Optional[Tuple[str, Any]]:
    """Check if target_skill_name matches any skill in profile_skills.

    Returns (matched_skill_name, confidence) or None.
    """
    if not target_skill_name or not profile_skills:
        return None

    clean_target = target_skill_name.strip().lower()
    norm_target = normalize_skill(target_skill_name).strip().lower()

    for p_item in profile_skills:
        p_name = ""
        p_conf: Any = None

        if isinstance(p_item, str):
            p_name = p_item
            p_conf = "Medium"
        elif isinstance(p_item, dict):
            p_name = (
                p_item.get("skill_name")
                or p_item.get("skill")
                or p_item.get("name")
                or p_item.get("canonical_name")
                or ""
            )
            p_conf = p_item.get("confidence", "Medium")
        elif hasattr(p_item, "skill") and hasattr(p_item.skill, "canonical_name"):
            p_name = p_item.skill.canonical_name
            p_conf = getattr(p_item, "confidence", "Medium")
        elif hasattr(p_item, "canonical_name"):
            p_name = p_item.canonical_name
            p_conf = getattr(p_item, "confidence", "Medium")
        elif hasattr(p_item, "skill_name"):
            p_name = p_item.skill_name
            p_conf = getattr(p_item, "confidence", "Medium")

        if not p_name:
            continue

        clean_p = p_name.strip().lower()
        norm_p = normalize_skill(p_name).strip().lower()

        if (
            clean_target == clean_p
            or norm_target == norm_p
            or clean_target == norm_p
            or norm_target == clean_p
        ):
            return p_name, p_conf

    return None


def classify_skill_status(
    skill: Union[Dict[str, Any], Any, str],
    profile_skills: Sequence[Any],
) -> str:
    """Classify candidate's relationship to a specific skill requirement.

    Returns one of:
        - "Matched": Skill in profile with High or Medium confidence.
        - "Partially Matched": Skill in profile with Low confidence.
        - "Missing": Required skill not found in candidate's profile.
        - "Optional": Skill is useful/optional but not required and not in profile.
    """
    skill_name, importance, required = _parse_skill_input(skill)
    match = _find_profile_match(skill_name, profile_skills)

    if match:
        _, conf = match
        # Check confidence level
        if isinstance(conf, str):
            c_lower = conf.strip().lower()
            if c_lower in ("high", "medium"):
                return "Matched"
            elif c_lower == "low":
                return "Partially Matched"
            return "Matched"
        elif isinstance(conf, (int, float)):
            if conf >= 0.45:
                return "Matched"
            return "Partially Matched"
        return "Matched"

    # Skill not present in profile
    if not required:
        return "Optional"
    return "Missing"


def calculate_readiness(
    profile_skills: Union[Sequence[Any], None],
    career_skills: Union[Sequence[Any], Dict[str, Any], None],
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None] = None,
    career_name: str = "Software Engineer",
) -> float:
    """Calculate career readiness score implementing the exact formula:

        RequiredSkillCoverage =
            weighted sum of required skills satisfied
            / weighted sum of all required skills

        Readiness = 100 * (
            0.70 * RequiredSkillCoverage
            + 0.20 * EvidenceCoverage
            + 0.10 * ExperienceAlignment
        )

    Clipped to [0, 100]. Returns float rounded to 2 decimal places.
    """
    if not career_skills:
        return 0.0

    profile_list = list(profile_skills or [])

    # Standardize career skills into (name, importance, required)
    standardized_skills: List[Tuple[str, float, bool]] = []
    if isinstance(career_skills, dict):
        req_list = career_skills.get("required_skills", [])
        for item in req_list:
            standardized_skills.append((str(item), 1.0, True))
    else:
        for item in career_skills:
            standardized_skills.append(_parse_skill_input(item))

    # Filter to required skills
    required_skills = [s for s in standardized_skills if s[2]]
    if not required_skills:
        # If no skill was explicitly flagged required=True, treat all as required
        required_skills = standardized_skills

    if not required_skills:
        return 0.0

    total_required_weight = 0.0
    satisfied_weight = 0.0
    evidence_weight = 0.0

    for name, importance, req in required_skills:
        weight = max(0.1, importance)
        total_required_weight += weight

        match = _find_profile_match(name, profile_list)
        if match:
            _, conf = match
            # Evaluate satisfaction and evidence based on confidence
            if isinstance(conf, str):
                c_lower = conf.strip().lower()
                if c_lower == "high":
                    sat_factor = 1.0
                    ev_factor = 1.0
                elif c_lower == "medium":
                    sat_factor = 1.0
                    ev_factor = 0.6
                else:  # low
                    sat_factor = 0.5
                    ev_factor = 0.3
            elif isinstance(conf, (int, float)):
                if conf >= 0.75:
                    sat_factor = 1.0
                    ev_factor = 1.0
                elif conf >= 0.45:
                    sat_factor = 1.0
                    ev_factor = 0.6
                else:
                    sat_factor = 0.5
                    ev_factor = 0.3
            else:
                sat_factor = 1.0
                ev_factor = 0.6

            satisfied_weight += weight * sat_factor
            evidence_weight += weight * ev_factor

    required_skill_coverage = (
        satisfied_weight / total_required_weight if total_required_weight > 0 else 0.0
    )
    evidence_coverage = (
        evidence_weight / total_required_weight if total_required_weight > 0 else 0.0
    )

    experience_alignment = calculate_experience_alignment(resume_sections, career_name)

    raw_readiness = 100.0 * (
        0.70 * required_skill_coverage
        + 0.20 * evidence_coverage
        + 0.10 * experience_alignment
    )

    return round(min(100.0, max(0.0, raw_readiness)), 2)


def get_skill_gaps(
    profile_skills: Union[Sequence[Any], None],
    career_skills: Union[Sequence[Any], Dict[str, Any], None],
) -> List[Dict[str, Any]]:
    """Identify and rank skill gaps (Missing or Partially Matched skills).

    Returns a list of dicts:
        {
            "skill_name": str,
            "status": "Missing" | "Partially Matched",
            "importance": float,
            "required": bool
        }
    Sorted by importance in descending order.
    """
    if not career_skills:
        return []

    profile_list = list(profile_skills or [])
    standardized_skills: List[Tuple[str, float, bool]] = []

    if isinstance(career_skills, dict):
        req_list = career_skills.get("required_skills", [])
        for item in req_list:
            standardized_skills.append((str(item), 1.0, True))
    else:
        for item in career_skills:
            standardized_skills.append(_parse_skill_input(item))

    gaps: List[Dict[str, Any]] = []

    for name, importance, required in standardized_skills:
        status = classify_skill_status(
            {"skill_name": name, "importance": importance, "required": required},
            profile_list,
        )

        if status in ("Missing", "Partially Matched"):
            gaps.append(
                {
                    "skill_name": name,
                    "status": status,
                    "importance": round(float(importance), 2),
                    "required": required,
                }
            )

    # Sort gaps by importance descending
    gaps.sort(key=lambda g: g["importance"], reverse=True)
    return gaps


def get_full_gap_report(
    profile_id: Union[UUID, str],
    career_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Generate a comprehensive skill gap and readiness report, persisting gaps to DB.

    1. Loads profile skills and resume sections from database.
    2. Loads career role and required career skills from database.
    3. Runs skill classification (Matched, Partially Matched, Missing).
    4. Calculates overall readiness.
    5. Identifies prioritized skill gaps.
    6. Saves gap records to the `skill_gaps` table.
    7. Returns complete report dictionary.
    """
    # 1. Fetch career role
    career = db.query(CareerRole).filter(CareerRole.id == career_id).first()
    if not career:
        raise ValueError(f"Career role with id {career_id} not found")

    # 2. Fetch career skills
    db_career_skills = (
        db.query(CareerSkill)
        .filter(CareerSkill.career_id == career_id)
        .join(CareerSkill.skill)
        .all()
    )

    career_skills_list: List[Dict[str, Any]] = []
    if db_career_skills:
        for cs in db_career_skills:
            career_skills_list.append(
                {
                    "skill_id": cs.skill_id,
                    "skill_name": cs.skill.canonical_name,
                    "importance": cs.importance if cs.importance is not None else 1.0,
                    "required": cs.required,
                }
            )
    elif career.name in CAREER_PROFILES:
        # Fallback to seeded definition if relationships are unlinked
        for s in CAREER_PROFILES[career.name]["required_skills"]:  # type: ignore
            career_skills_list.append(
                {
                    "skill_name": str(s),
                    "importance": 1.0,
                    "required": True,
                }
            )

    # 3. Fetch profile skills
    db_profile_skills = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == profile_id)
        .join(ProfileSkill.skill)
        .all()
    )

    profile_skills_list: List[Dict[str, Any]] = []
    for ps in db_profile_skills:
        profile_skills_list.append(
            {
                "skill_id": ps.skill_id,
                "skill_name": ps.skill.canonical_name,
                "confidence": ps.confidence if ps.confidence is not None else 0.8,
                "is_verified": bool(getattr(ps, "is_verified", False)),
                "verified_score": getattr(ps, "verified_score", None),
            }
        )

    # 4. Fetch resume sections for experience alignment
    resume = (
        db.query(Resume)
        .filter(Resume.profile_id == profile_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    resume_sections: Dict[str, str] = {}
    if resume and resume.sections:
        resume_sections = {s.section_type: s.text or "" for s in resume.sections}
    else:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if profile:
            if profile.experience_summary:
                resume_sections["experience"] = profile.experience_summary
            if profile.education_summary:
                resume_sections["education"] = profile.education_summary

    # 5. Classify skills
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    partial_skills: List[str] = []

    for cs in career_skills_list:
        status = classify_skill_status(cs, profile_skills_list)
        s_name = cs["skill_name"]
        if status == "Matched":
            matched_skills.append(s_name)
        elif status == "Partially Matched":
            partial_skills.append(s_name)
        elif status == "Missing":
            missing_skills.append(s_name)

    # 6. Calculate Readiness
    readiness = calculate_readiness(
        profile_skills=profile_skills_list,
        career_skills=career_skills_list,
        resume_sections=resume_sections,
        career_name=career.name,
    )

    # 7. Get prioritized skill gaps
    skill_gaps = get_skill_gaps(
        profile_skills=profile_skills_list,
        career_skills=career_skills_list,
    )

    # 8. Save results to skill_gaps table
    try:
        # Clear existing gaps for this profile + career
        db.query(SkillGap).filter(
            SkillGap.profile_id == profile_id,
            SkillGap.career_id == career_id,
        ).delete()

        # Cache skills dictionary by lowercase name for fast id lookup
        skills_cache = {
            s.canonical_name.lower(): s.id for s in db.query(Skill).all()
        }

        for gap in skill_gaps:
            name_key = gap["skill_name"].lower()
            skill_id = skills_cache.get(name_key)
            if not skill_id:
                norm_key = normalize_skill(gap["skill_name"]).lower()
                skill_id = skills_cache.get(norm_key)

            if skill_id:
                new_gap = SkillGap(
                    profile_id=profile_id,
                    career_id=career_id,
                    skill_id=skill_id,
                    status=gap["status"],
                    importance=gap["importance"],
                )
                db.add(new_gap)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Warning] Failed to persist skill_gaps to database: {e}")

    # 9. Return structured report
    verified_skills = [
        ps.skill.canonical_name for ps in db_profile_skills if getattr(ps, "is_verified", False)
    ]
    return {
        "career_name": career.name,
        "readiness": readiness,
        "matched_skills": matched_skills,
        "verified_skills": verified_skills,
        "missing_skills": missing_skills,
        "partial_skills": partial_skills,
        "skill_gaps": skill_gaps,
    }

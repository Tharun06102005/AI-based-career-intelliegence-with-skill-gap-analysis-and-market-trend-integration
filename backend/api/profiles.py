"""Profile endpoints: fetch a profile with skills, update its summaries."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import Profile
from models.session import get_db

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class ProfileUpdate(BaseModel):
    """Partial update payload — both fields optional."""

    education_summary: Optional[str] = None
    experience_summary: Optional[str] = None


def _serialize(profile: Profile) -> dict:
    """Profile dict with its skills joined in."""
    skills = [
        {
            "skill_id": ps.skill_id,
            "canonical_name": ps.skill.canonical_name if ps.skill else None,
            "category": ps.skill.category if ps.skill else None,
            "confidence": ps.confidence,
            "evidence_ref": ps.evidence_ref,
        }
        for ps in profile.profile_skills
    ]
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "education_summary": profile.education_summary,
        "experience_summary": profile.experience_summary,
        "created_at": profile.created_at.isoformat(),
        "skills": skills,
    }


@router.get("/{profile_id}")
def get_profile(profile_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return a profile together with its skills."""
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(profile)


@router.put("/{profile_id}")
def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """Update education/experience summaries (only fields provided are changed)."""
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    if payload.education_summary is not None:
        profile.education_summary = payload.education_summary
    if payload.experience_summary is not None:
        profile.experience_summary = payload.experience_summary

    db.commit()
    db.refresh(profile)
    return _serialize(profile)

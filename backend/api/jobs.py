"""Job and Internship Matching API router.

Endpoints:
- GET  /api/jobs                                : List ranked opportunities with filters
- GET  /api/jobs/{opportunity_id}/match/{profile_id}: Detailed match breakdown
- POST /api/jobs/track                          : Save opportunity or update application status
- GET  /api/jobs/tracker/{profile_id}           : Retrieve all tracked applications
- POST /api/jobs/import-csv                     : Import opportunities from CSV
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user
from models.database import JobOpportunity, Profile, ProfileSkill, User, UserOpportunity
from models.session import get_db
from services.job_matcher import (
    calculate_opportunity_match,
    get_matched_opportunities,
    get_tracked_applications,
    import_opportunities_from_csv,
    update_application_status,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class TrackOpportunityRequest(BaseModel):
    """Payload to save an opportunity or update application status."""
    profile_id: UUID
    opportunity_id: int
    status: str = Field(default="Saved", description="Saved, Applied, Assessment, Interview, Offer, Rejected")
    notes: Optional[str] = None


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK, include_in_schema=False)
def list_opportunities(
    profile_id: UUID = Query(..., description="Candidate profile ID to compute match scores for"),
    opportunity_type: Optional[str] = Query(None, description="All, Full-time, Internship, Contract"),
    work_mode: Optional[str] = Query(None, description="All, Remote, Hybrid, On-site"),
    min_salary: Optional[float] = Query(None, description="Minimum salary filter"),
    search: Optional[str] = Query(None, description="Keyword search in title, company, or description"),
    sort_by: str = Query("match_score", description="match_score, date_posted, or salary"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve opportunities scored and ranked according to candidate verified and claimed skills."""
    return get_matched_opportunities(
        profile_id=profile_id,
        db=db,
        opportunity_type=opportunity_type,
        work_mode=work_mode,
        min_salary=min_salary,
        search_query=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )


@router.get("/{opportunity_id}/match/{profile_id}", status_code=status.HTTP_200_OK)
def get_opportunity_match_details(
    opportunity_id: int,
    profile_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return in-depth match explanation for an opportunity."""
    opp = db.query(JobOpportunity).filter(JobOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")

    profile_skills_records = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == profile_id)
        .join(ProfileSkill.skill)
        .all()
    )

    profile_skills = [
        {
            "skill_name": ps.skill.canonical_name,
            "confidence": ps.confidence,
            "is_verified": ps.is_verified,
            "verified_score": ps.verified_score,
        }
        for ps in profile_skills_records
    ]

    match_data = calculate_opportunity_match(profile_skills, opp)
    return {
        "opportunity_id": opp.id,
        "title": opp.title,
        "company_name": opp.company_name,
        "location": opp.location,
        "work_mode": opp.work_mode,
        "opportunity_type": opp.opportunity_type,
        "experience_level": opp.experience_level,
        "min_salary": opp.min_salary,
        "max_salary": opp.max_salary,
        "currency": opp.currency,
        "description": opp.description,
        "application_url": opp.application_url,
        "is_verified": opp.is_verified,
        "source": opp.source,
        **match_data,
    }


@router.post("/track", status_code=status.HTTP_200_OK)
def track_opportunity(
    payload: TrackOpportunityRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Save an opportunity or update application status in candidate pipeline."""
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to profile.")

    entry = update_application_status(
        profile_id=payload.profile_id,
        opportunity_id=payload.opportunity_id,
        status=payload.status,
        notes=payload.notes,
        db=db,
    )

    return {
        "id": entry.id,
        "opportunity_id": entry.opportunity_id,
        "status": entry.status,
        "notes": entry.notes,
        "updated_at": entry.updated_at.isoformat(),
    }


@router.get("/tracker/{profile_id}", status_code=status.HTTP_200_OK)
def list_tracked_opportunities(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve all tracked applications for a profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to tracker.")

    return get_tracked_applications(profile_id, db)


@router.post("/import-csv", status_code=status.HTTP_200_OK)
async def import_csv_opportunities(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ingest opportunities from uploaded CSV file with automatic deduplication."""
    content = await file.read()
    csv_text = content.decode("utf-8", errors="replace")
    result = import_opportunities_from_csv(csv_text, db, source_label=f"csv_{file.filename}")
    return result

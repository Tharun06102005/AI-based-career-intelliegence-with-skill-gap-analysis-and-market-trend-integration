"""Skill gaps router.

Provides endpoints for evaluating skill gaps, assessing career readiness,
persisting gap analysis records to the database, and retrieving gap reports.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.session import get_db
from scoring.gap_engine import get_full_gap_report

router = APIRouter(prefix="/api/gaps", tags=["gaps"])


class GapAnalysisRequest(BaseModel):
    """Payload to trigger skill gap analysis."""

    profile_id: UUID = Field(..., description="UUID of candidate profile")
    career_id: int = Field(..., description="ID of canonical career role")


class SkillGapItem(BaseModel):
    """Individual skill gap item."""

    skill_name: str
    status: str
    importance: float
    required: bool


class GapReportResponse(BaseModel):
    """Complete skill gap and readiness response."""

    career_name: str
    readiness: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    partial_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[SkillGapItem] = Field(default_factory=list)


@router.post("", response_model=GapReportResponse, status_code=status.HTTP_200_OK)
@router.post(
    "/",
    response_model=GapReportResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def analyze_skill_gaps(
    payload: GapAnalysisRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Execute skill gap and readiness analysis for a candidate profile against a career role.

    Saves results to the skill_gaps table and returns the complete gap report.
    """
    try:
        report = get_full_gap_report(
            profile_id=payload.profile_id,
            career_id=payload.career_id,
            db=db,
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate gap report: {str(e)}",
        )


@router.get("/{profile_id}/{career_id}", response_model=GapReportResponse)
def get_gap_report(
    profile_id: UUID,
    career_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve or compute skill gap analysis for a specific profile and career role."""
    try:
        return get_full_gap_report(
            profile_id=profile_id,
            career_id=career_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gap report: {str(e)}",
        )

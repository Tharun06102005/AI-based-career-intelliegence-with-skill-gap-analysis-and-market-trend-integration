"""Skill Verification and Adaptive Assessment API router.

Endpoints:
- GET  /api/assessments/skills                : List assessable skills and questions
- POST /api/assessments/start                 : Start new assessment attempt
- GET  /api/assessments/{attempt_id}/next     : Fetch next adaptive question
- POST /api/assessments/{attempt_id}/submit   : Submit answer (runs sandboxed test cases if coding)
- POST /api/assessments/{attempt_id}/complete : Finalize attempt and update verified skills
- GET  /api/assessments/history/{profile_id}  : Retrieve paginated attempt history
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user
from models.database import AssessmentAttempt, Profile, User
from models.session import get_db
from services.assessment_engine import (
    complete_attempt,
    get_assessment_history,
    get_available_skills,
    get_next_question,
    start_assessment_attempt,
    submit_answer,
)

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


class StartAssessmentRequest(BaseModel):
    """Payload to start a skill assessment."""
    profile_id: UUID = Field(..., description="UUID of candidate profile")
    skill_name: str = Field(..., description="Target skill name (e.g. Python, SQL, React)")
    initial_difficulty: str = Field(default="Intermediate", description="Beginner, Intermediate, or Advanced")


class SubmitAnswerRequest(BaseModel):
    """Payload to submit answer for an assessment question."""
    question_id: int
    user_answer: str


@router.get("/skills", status_code=status.HTTP_200_OK)
def list_assessable_skills(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """List technical skills available for assessment with question counts and difficulties."""
    return get_available_skills(db)


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_assessment(
    payload: StartAssessmentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Start a new skill verification assessment attempt."""
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile access not authorized.")

    attempt = start_assessment_attempt(
        profile_id=payload.profile_id,
        skill_name=payload.skill_name,
        initial_difficulty=payload.initial_difficulty,
        db=db,
    )

    first_question = get_next_question(attempt.id, db)

    return {
        "attempt_id": attempt.id,
        "skill_name": attempt.skill_name,
        "difficulty": attempt.difficulty,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "first_question": first_question,
    }


@router.get("/{attempt_id}/next", status_code=status.HTTP_200_OK)
def fetch_next_question(
    attempt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve the next adaptive question for the active attempt."""
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found.")

    profile = db.query(Profile).filter(Profile.id == attempt.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to attempt.")

    question = get_next_question(attempt_id, db)
    if not question:
        return {
            "has_more": False,
            "message": "No further questions remaining for this assessment. You can now complete the attempt.",
            "question": None,
        }

    return {
        "has_more": True,
        "current_difficulty": attempt.difficulty,
        "question": question,
    }


@router.post("/{attempt_id}/submit", status_code=status.HTTP_200_OK)
def submit_question_answer(
    attempt_id: int,
    payload: SubmitAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submit candidate answer and evaluate."""
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found.")

    profile = db.query(Profile).filter(Profile.id == attempt.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to attempt.")

    try:
        result = submit_answer(
            attempt_id=attempt_id,
            question_id=payload.question_id,
            user_answer=payload.user_answer,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{attempt_id}/complete", status_code=status.HTTP_200_OK)
def finalize_attempt(
    attempt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Complete assessment attempt, compute score, and update verified skill status."""
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found.")

    profile = db.query(Profile).filter(Profile.id == attempt.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to attempt.")

    return complete_attempt(attempt_id, db)


@router.get("/history/{profile_id}", status_code=status.HTTP_200_OK)
def list_history(
    profile_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve candidate assessment attempt history with pagination."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to history.")

    return get_assessment_history(profile_id, db, limit=limit, offset=offset)

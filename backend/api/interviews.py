"""AI Mock Interview Coach API router.

Endpoints:
- POST /api/interviews/start                  : Create new interview session
- GET  /api/interviews/{session_id}/question  : Generate or fetch current question
- POST /api/interviews/{session_id}/answer    : Submit answer and obtain rubric feedback
- POST /api/interviews/{session_id}/finish    : Complete session and get final scorecard
- GET  /api/interviews/history/{profile_id}   : Retrieve interview session history
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user
from models.database import CareerRole, InterviewSession, InterviewTurn, Profile, User
from models.session import get_db
from services.interview_coach import (
    evaluate_candidate_answer,
    finish_interview_session,
    generate_interview_question,
    get_interview_history,
)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


class StartInterviewRequest(BaseModel):
    """Payload to start a mock interview practice session."""
    profile_id: UUID
    role_name: str = Field(..., description="Target role (e.g. Software Engineer, Backend Developer)")
    category: str = Field(default="technical", description="technical, coding, project_defense, resume_based, hr")
    difficulty: str = Field(default="Intermediate", description="Beginner, Intermediate, Advanced")
    duration_minutes: int = Field(default=30, ge=10, le=90)


class SubmitInterviewAnswerRequest(BaseModel):
    """Payload to submit answer for the current question."""
    turn_id: int
    user_answer: str


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_interview(
    payload: StartInterviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Initialize a mock interview session tailored to the candidate's target role and resume."""
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile access unauthorized.")

    career = db.query(CareerRole).filter(CareerRole.name.ilike(payload.role_name)).first()

    session = InterviewSession(
        profile_id=payload.profile_id,
        career_id=career.id if career else None,
        role_name=payload.role_name,
        category=payload.category,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Generate first question
    first_question = generate_interview_question(session.id, db)

    return {
        "session_id": session.id,
        "role_name": session.role_name,
        "category": session.category,
        "difficulty": session.difficulty,
        "status": session.status,
        "current_question": first_question,
    }


@router.get("/{session_id}/question", status_code=status.HTTP_200_OK)
def fetch_question(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generate or retrieve next interview question for this active session."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    profile = db.query(Profile).filter(Profile.id == session.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to interview session.")

    if session.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session has already ended.")

    # Check if there is an existing unanswered turn
    last_turn = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_number.desc())
        .first()
    )

    if last_turn and last_turn.user_answer is None:
        return {
            "turn_id": last_turn.id,
            "turn_number": last_turn.turn_number,
            "question": last_turn.question_text,
            "category": last_turn.question_type,
            "context_snippet": last_turn.context_snippet,
        }

    return generate_interview_question(session_id, db)


@router.post("/{session_id}/answer", status_code=status.HTTP_200_OK)
def submit_answer(
    session_id: int,
    payload: SubmitInterviewAnswerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submit answer to current interview question and receive 5-dimension rubric critique."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    profile = db.query(Profile).filter(Profile.id == session.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to interview session.")

    return evaluate_candidate_answer(payload.turn_id, payload.user_answer, db)


@router.post("/{session_id}/finish", status_code=status.HTTP_200_OK)
def finalize_interview(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Complete interview session and obtain performance summary report."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    profile = db.query(Profile).filter(Profile.id == session.profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to interview session.")

    return finish_interview_session(session_id, db)


@router.get("/history/{profile_id}", status_code=status.HTTP_200_OK)
def list_interview_history(
    profile_id: UUID,
    limit: int = Query(15, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve history of mock interview sessions for a profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile or profile.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to history.")

    return get_interview_history(profile_id, db, limit=limit, offset=offset)

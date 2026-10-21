"""Progress Tracking API router.

Provides endpoints for updating learning progress on technical resources
and retrieving profile-wide learning status and completion statistics.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import Profile, Progress, Resource
from models.session import get_db
from schemas.resource import ProfileProgressSummary, ProgressResponse, ProgressUpdate, ResourceResponse

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.post("", response_model=ProgressResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=ProgressResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def update_learning_progress(
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Record or update candidate progress on a learning resource.

    Validates status ('not_started', 'in_progress', 'completed') and progress (0-100).
    """
    # 1. Validate profile existence
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{payload.profile_id}' not found.",
        )

    # 2. Validate resource existence
    resource = db.query(Resource).filter(Resource.id == payload.resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning resource with id {payload.resource_id} not found.",
        )

    # 3. Normalize status and progress
    norm_status = payload.status.strip().lower()
    if norm_status not in ("not_started", "in_progress", "completed"):
        norm_status = "in_progress"

    progress_val = float(payload.progress)
    if norm_status == "completed" and progress_val < 100.0:
        progress_val = 100.0
    elif progress_val >= 100.0:
        norm_status = "completed"
        progress_val = 100.0

    # 4. Upsert progress entry
    progress_entry = (
        db.query(Progress)
        .filter(
            Progress.profile_id == payload.profile_id,
            Progress.resource_id == payload.resource_id,
        )
        .first()
    )

    if progress_entry:
        progress_entry.status = norm_status
        progress_entry.progress = progress_val
        progress_entry.updated_at = datetime.utcnow()
    else:
        progress_entry = Progress(
            profile_id=payload.profile_id,
            resource_id=payload.resource_id,
            status=norm_status,
            progress=progress_val,
            updated_at=datetime.utcnow(),
        )
        db.add(progress_entry)

    db.commit()
    db.refresh(progress_entry)

    return {
        "id": progress_entry.id,
        "profile_id": str(progress_entry.profile_id),
        "resource_id": progress_entry.resource_id,
        "status": progress_entry.status,
        "progress": progress_entry.progress,
        "updated_at": progress_entry.updated_at,
        "resource": {
            "id": resource.id,
            "skill_name": resource.skill.canonical_name if resource.skill else None,
            "title": resource.title,
            "url": resource.url,
            "provider": resource.provider,
            "resource_type": resource.resource_type,
        },
    }


@router.get("/{profile_id}", response_model=ProfileProgressSummary, status_code=status.HTTP_200_OK)
def get_profile_progress(
    profile_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve all learning progress entries and aggregate completion statistics for a profile."""
    # 1. Validate profile
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{profile_id}' not found.",
        )

    # 2. Fetch progress entries with resources
    entries = (
        db.query(Progress)
        .filter(Progress.profile_id == profile_id)
        .join(Progress.resource)
        .all()
    )

    formatted_entries: List[Dict[str, Any]] = []
    completed_count = 0
    in_progress_count = 0
    total_progress_sum = 0.0

    for e in entries:
        r = e.resource
        res_info = None
        if r:
            res_info = {
                "id": r.id,
                "skill_name": r.skill.canonical_name if r.skill else None,
                "title": r.title,
                "url": r.url,
                "provider": r.provider,
                "resource_type": r.resource_type,
            }

        if e.status == "completed" or (e.progress and e.progress >= 100.0):
            completed_count += 1
        elif e.status == "in_progress":
            in_progress_count += 1

        total_progress_sum += float(e.progress or 0.0)

        formatted_entries.append({
            "id": e.id,
            "profile_id": str(e.profile_id),
            "resource_id": e.resource_id,
            "status": e.status,
            "progress": float(e.progress or 0.0),
            "updated_at": e.updated_at,
            "resource": res_info,
        })

    total_tracked = len(formatted_entries)
    avg_progress = (
        round(total_progress_sum / total_tracked, 2) if total_tracked > 0 else 0.0
    )

    return {
        "profile_id": str(profile_id),
        "total_tracked": total_tracked,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
        "average_progress": avg_progress,
        "entries": formatted_entries,
    }

"""Pydantic schemas for Learning Resources and Progress Tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    """Details of a single learning resource."""

    id: Optional[int] = None
    skill_name: Optional[str] = None
    title: str
    url: Optional[str] = None
    provider: Optional[str] = None
    resource_type: Optional[str] = "docs"


class GapResourcesResponse(BaseModel):
    """Mapping of missing skills to their curated learning resources."""

    profile_id: str
    career_id: int
    career_name: str
    missing_skills: List[str] = Field(default_factory=list)
    resources_by_skill: Dict[str, List[ResourceResponse]] = Field(
        default_factory=dict
    )


class ProgressUpdate(BaseModel):
    """Payload to record or update learning progress for a resource."""

    profile_id: Union[UUID, str] = Field(..., description="UUID of candidate profile")
    resource_id: int = Field(..., description="Database ID of target resource")
    status: str = Field(
        "in_progress",
        description="Learning status: 'not_started', 'in_progress', or 'completed'",
    )
    progress: int = Field(
        ...,
        ge=0,
        le=100,
        description="Progress percentage integer between 0 and 100",
    )


class ProgressResponse(BaseModel):
    """Recorded progress entry including resource information."""

    id: int
    profile_id: str
    resource_id: int
    status: str
    progress: float
    updated_at: datetime
    resource: Optional[ResourceResponse] = None


class ProfileProgressSummary(BaseModel):
    """Aggregate learning progress summary for a candidate profile."""

    profile_id: str
    total_tracked: int
    completed_count: int
    in_progress_count: int
    average_progress: float
    entries: List[ProgressResponse] = Field(default_factory=list)

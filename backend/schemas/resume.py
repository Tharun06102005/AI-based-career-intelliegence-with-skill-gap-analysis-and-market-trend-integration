"""Pydantic response schemas for the resume endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SkillInResume(BaseModel):
    """One extracted skill attached to a resume, with its evidence."""

    skill_name: str
    confidence: Optional[str] = None
    section: Optional[str] = None
    raw_text: Optional[str] = None
    is_verified: bool = False
    verified_score: Optional[float] = None
    verified_level: Optional[str] = None


class ResumeScore(BaseModel):
    """Resume scorecard rating and section coverage."""

    total_score: int
    grade: str
    sections_found: List[str] = Field(default_factory=list)
    sections_missing: List[str] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    """Payload returned after a successful upload + pipeline run."""

    resume_id: UUID
    status: str
    skills_count: int
    sections_found: List[str] = Field(default_factory=list)
    skills: List[SkillInResume] = Field(default_factory=list)
    resume_score: Optional[ResumeScore] = None


class ResumeDetailResponse(BaseModel):
    """Resume details, detected sections, and extracted skills."""

    resume_id: UUID
    filename: Optional[str] = None
    status: str
    uploaded_at: datetime
    sections: Dict[str, str] = Field(default_factory=dict)
    skills: List[SkillInResume] = Field(default_factory=list)
    resume_score: Optional[ResumeScore] = None


class ATSCheckRequest(BaseModel):
    """Payload to evaluate resume ATS compatibility against a job description."""

    resume_id: Optional[UUID] = None
    resume_text: Optional[str] = None
    job_description: str


class ATSCheckResponse(BaseModel):
    """ATS scoring output with keyword match and recommendations."""

    ats_score: int
    match_percentage: int
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


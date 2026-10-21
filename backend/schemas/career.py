"""Pydantic schemas for Careers, Ranking, and Comparison APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class CareerRankRequest(BaseModel):
    """Request payload for ranking careers for a profile."""

    profile_id: Union[UUID, str] = Field(
        ..., description="UUID of candidate profile to rank careers for"
    )


class CareerSkillItem(BaseModel):
    """Skill requirement item with importance and required flag."""

    skill_name: str
    importance: float = 1.0
    required: bool = True


class CareerResponse(BaseModel):
    """Basic career role response schema."""

    id: int
    name: str
    description: Optional[str] = None
    demand_score: float = 0.0
    required_skills: List[str] = Field(default_factory=list)


class CareerDetailResponse(BaseModel):
    """Detailed career role response schema with weights and job counts."""

    id: int
    name: str
    description: Optional[str] = None
    required_skills: List[CareerSkillItem] = Field(default_factory=list)
    demand_score: float = 0.0
    job_count: int = 0


class CareerComponents(BaseModel):
    """Individual CareerFit component breakdown."""

    skill_match: float
    evidence_strength: float
    experience_alignment: float
    education_alignment: float
    market_demand: float


class CareerRankResult(BaseModel):
    """Individual career ranking result."""

    career_id: int
    career_name: str
    total_score: float
    components: CareerComponents
    engine_version: str = "score-1.0"
    demand_score: float = 0.0


class CareerCompareRequest(BaseModel):
    """Request payload to compare exactly two career roles."""

    profile_id: Union[UUID, str] = Field(
        ..., description="UUID of candidate profile"
    )
    career_ids: List[int] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="List containing exactly two career IDs to compare",
    )


class CareerComparisonItem(BaseModel):
    """Comparison item for one career role."""

    career_name: str
    fit_score: float
    readiness: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    demand_score: float = 0.0
    effort_to_reach: str = Field(
        ..., description="'Low' (0-2 missing), 'Medium' (3-4 missing), 'High' (5+ missing)"
    )


class CareerCompareResponse(BaseModel):
    """Side-by-side comparison response payload for two careers."""

    profile_id: str
    comparisons: List[CareerComparisonItem] = Field(
        ..., min_length=2, max_length=2
    )
    careers: Optional[List[CareerComparisonItem]] = Field(
        default=None, description="Alias matching comparisons list"
    )

    def model_post_init(self, __context: Any) -> None:
        if self.careers is None:
            self.careers = self.comparisons


class CareerPathResponse(BaseModel):
    """Career path progression with candidate's current assessed level."""

    career_id: int
    career_name: str
    path: Dict[str, Any]
    current_level: str
    current_level_match: float
    next_level: str
    skills_to_advance: List[str] = Field(default_factory=list)
    levels_away: int


class SkillTrendItem(BaseModel):
    """Market trend metric item for a specific skill."""

    skill: str
    job_count: int
    trend_score: float
    trend_label: str

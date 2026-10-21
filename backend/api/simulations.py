"""Simulations API router.

Provides endpoints for running what-if career simulations, assessing the impact
of hypothetical skill additions and removals on career fit and readiness, and
retrieving historical simulation results.
"""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.session import get_db
from simulation.what_if_engine import get_simulation_result, run_simulation

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


class SimulationPreviewRequest(BaseModel):
    """Payload to trigger what-if career simulation preview."""

    profile_id: UUID = Field(..., description="UUID of candidate profile")
    career_id: int = Field(..., description="ID of canonical career role")
    add_skills: List[str] = Field(
        default_factory=list,
        description="List of skills to add hypothetically with High confidence",
    )
    remove_skills: List[str] = Field(
        default_factory=list,
        description="List of skills to remove hypothetically",
    )


class SimulationMetricSnapshot(BaseModel):
    """Snapshot of scoring and readiness metrics."""

    career_fit_score: float
    readiness: float
    missing_skills_count: int


class SimulationDeltaSnapshot(BaseModel):
    """Delta between simulated and baseline metrics."""

    career_fit_score: float
    readiness: float
    missing_skills_count: int


class SimulationResponse(BaseModel):
    """Complete response payload for a simulation."""

    simulation_id: int
    profile_id: str
    career_id: int
    baseline: SimulationMetricSnapshot
    simulated: SimulationMetricSnapshot
    delta: SimulationDeltaSnapshot
    added_skills: List[str] = Field(default_factory=list)
    removed_skills: List[str] = Field(default_factory=list)


@router.post(
    "/preview",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
)
def preview_simulation(
    payload: SimulationPreviewRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Execute what-if simulation comparing baseline against simulated profile.

    Reuses exact career scoring and readiness engine formulas without duplication.
    """
    try:
        result = run_simulation(
            profile_id=payload.profile_id,
            career_id=payload.career_id,
            add_skills=payload.add_skills,
            remove_skills=payload.remove_skills,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        )


@router.get("/{simulation_id}", response_model=SimulationResponse)
def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch stored simulation results by ID."""
    try:
        return get_simulation_result(simulation_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch simulation: {str(e)}",
        )

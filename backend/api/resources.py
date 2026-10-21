"""Learning Resources API router.

Provides endpoints for querying technical learning resources by skill name
and retrieving curated remediation resources for detected skill gaps.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import CareerRole, Resource, Skill
from models.session import get_db
from schemas.resource import GapResourcesResponse, ResourceResponse
from scoring.gap_engine import get_full_gap_report
from services.resource_mapper import (
    ensure_resources_in_db,
    get_resources_for_gaps,
    get_resources_for_skill,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=List[ResourceResponse], status_code=status.HTTP_200_OK)
@router.get("/", response_model=List[ResourceResponse], status_code=status.HTTP_200_OK, include_in_schema=False)
def get_resources(
    skill: Optional[str] = Query(None, description="Skill name to fetch resources for"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Fetch learning resources for a specific skill, or list verified library resources."""
    # Ensure database resources are seeded for id resolution
    ensure_resources_in_db(db)

    if skill and skill.strip():
        items = get_resources_for_skill(skill)
        # Attach database resource id if available
        results: List[Dict[str, Any]] = []
        for r in items:
            title = r["title"]
            db_res = db.query(Resource).filter(Resource.title == title).first()
            results.append({
                "id": db_res.id if db_res else None,
                "skill_name": r.get("skill_name", skill),
                "title": r["title"],
                "url": r.get("url"),
                "provider": r.get("provider"),
                "resource_type": r.get("resource_type", "docs"),
            })
        return results

    # If no specific skill queried, return top curated library resources from database
    db_resources = db.query(Resource).join(Resource.skill).limit(100).all()
    return [
        {
            "id": res.id,
            "skill_name": res.skill.canonical_name if res.skill else "General",
            "title": res.title,
            "url": res.url,
            "provider": res.provider,
            "resource_type": res.resource_type,
        }
        for res in db_resources
    ]


@router.get("/gaps/{profile_id}/{career_id}", response_model=GapResourcesResponse, status_code=status.HTTP_200_OK)
def get_gap_resources(
    profile_id: UUID,
    career_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve curated learning resources targeting all identified skill gaps for a career role."""
    ensure_resources_in_db(db)

    # 1. Fetch gap report
    try:
        gap_report = get_full_gap_report(
            profile_id=profile_id,
            career_id=career_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    missing_skills = gap_report.get("missing_skills", [])
    # Also combine partial skills if any
    all_gaps = list(missing_skills)
    for p in gap_report.get("partial_skills", []):
        if p not in all_gaps:
            all_gaps.append(p)

    # 2. Map gaps to resources
    resources_by_skill = get_resources_for_gaps(all_gaps)

    # Attach database IDs
    formatted_dict: Dict[str, List[Dict[str, Any]]] = {}
    for s_name, res_list in resources_by_skill.items():
        formatted_list: List[Dict[str, Any]] = []
        for r in res_list:
            db_res = db.query(Resource).filter(Resource.title == r["title"]).first()
            formatted_list.append({
                "id": db_res.id if db_res else None,
                "skill_name": s_name,
                "title": r["title"],
                "url": r.get("url"),
                "provider": r.get("provider"),
                "resource_type": r.get("resource_type", "docs"),
            })
        formatted_dict[s_name] = formatted_list

    return {
        "profile_id": str(profile_id),
        "career_id": career_id,
        "career_name": gap_report.get("career_name", "Target Career"),
        "missing_skills": missing_skills,
        "resources_by_skill": formatted_dict,
    }

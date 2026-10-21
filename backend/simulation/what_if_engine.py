"""What-If Career Simulator Engine.

CRITICAL RULE:
    The simulator MUST call the exact same functions from scoring/career_scorer.py
    and scoring/gap_engine.py. It never duplicates scoring or gap analysis logic.

Allows users to simulate acquiring or removing technical skills, predicting the
exact impact on CareerFit score, market readiness, and missing skill gaps.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID

from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import (
    CareerRole,
    CareerSkill,
    Profile,
    ProfileSkill,
    Resume,
    Skill,
    Simulation,
    SimulationChange,
    SimulationResult,
)
from scoring.career_scorer import calculate_career_fit
from scoring.gap_engine import calculate_readiness, get_skill_gaps
from services.career_seeder import CAREER_PROFILES
from services.skill_normalizer import normalize_skill


def create_simulation_state(
    profile_skills: Union[Sequence[Any], None],
    add_skills: Optional[Sequence[str]] = None,
    remove_skills: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Clone and modify a candidate's profile skills hypothetically.

    Rules:
        - Clones current profile_skills list.
        - Adds hypothetical skills with 'High' confidence.
        - Removes specified skills.
        - Returns temporary modified skills list.
        - NEVER modifies the original profile_skills.
    """
    # 1. Standardize and deeply clone current skills
    cloned_skills: List[Dict[str, Any]] = []

    if profile_skills:
        for item in profile_skills:
            if isinstance(item, str):
                cloned_skills.append({"skill_name": item, "confidence": "Medium"})
            elif isinstance(item, dict):
                cloned_skills.append(dict(item))
            elif hasattr(item, "skill") and hasattr(item.skill, "canonical_name"):
                cloned_skills.append({
                    "skill_name": item.skill.canonical_name,
                    "confidence": getattr(item, "confidence", "Medium") or "Medium",
                })
            elif hasattr(item, "canonical_name"):
                cloned_skills.append({
                    "skill_name": item.canonical_name,
                    "confidence": getattr(item, "confidence", "Medium") or "Medium",
                })
            elif hasattr(item, "skill_name"):
                cloned_skills.append({
                    "skill_name": item.skill_name,
                    "confidence": getattr(item, "confidence", "Medium") or "Medium",
                })

    # 2. Build set of normalized names to remove
    remove_set = set()
    for r in (remove_skills or []):
        r_str = str(r).strip()
        if r_str:
            remove_set.add(r_str.lower())
            remove_set.add(normalize_skill(r_str).lower())

    # 3. Filter out removed skills
    active_skills: List[Dict[str, Any]] = []
    for item in cloned_skills:
        s_name = str(item.get("skill_name", "")).strip()
        s_norm = normalize_skill(s_name).strip().lower()
        if s_name.lower() not in remove_set and s_norm not in remove_set:
            active_skills.append(item)

    # 4. Add new hypothetical skills with High confidence
    for a in (add_skills or []):
        a_str = str(a).strip()
        if not a_str:
            continue

        a_norm = normalize_skill(a_str)
        a_lower = a_norm.lower()

        # Check if already in active skills
        existing = None
        for item in active_skills:
            cur_norm = normalize_skill(item.get("skill_name", "")).lower()
            if cur_norm == a_lower:
                existing = item
                break

        if existing:
            # Upgrade confidence to High for simulated capability
            existing["confidence"] = "High"
        else:
            active_skills.append({
                "skill_name": a_norm or a_str,
                "confidence": "High",
            })

    return active_skills


def run_simulation(
    profile_id: Union[UUID, str],
    career_id: int,
    add_skills: Optional[Sequence[str]] = None,
    remove_skills: Optional[Sequence[str]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Execute a what-if simulation comparing baseline vs simulated career fit & readiness.

    Calls the EXACT same functions from career_scorer.py and gap_engine.py.
    Persists simulation records to simulations and simulation_results tables.
    """
    if db is None:
        raise ValueError("Database session is required to run a simulation.")

    # 1. Load career role
    career = db.query(CareerRole).filter(CareerRole.id == career_id).first()
    if not career:
        raise ValueError(f"Career role with id {career_id} not found")

    # 2. Load career skills
    db_career_skills = (
        db.query(CareerSkill)
        .filter(CareerSkill.career_id == career_id)
        .join(CareerSkill.skill)
        .all()
    )

    career_skills_list: List[Dict[str, Any]] = []
    if db_career_skills:
        for cs in db_career_skills:
            career_skills_list.append({
                "skill_id": cs.skill_id,
                "skill_name": cs.skill.canonical_name,
                "importance": cs.importance if cs.importance is not None else 1.0,
                "required": cs.required,
            })
    elif career.name in CAREER_PROFILES:
        for s in CAREER_PROFILES[career.name]["required_skills"]:  # type: ignore
            career_skills_list.append({
                "skill_name": str(s),
                "importance": 1.0,
                "required": True,
            })

    # 3. Load baseline profile skills
    db_profile_skills = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == profile_id)
        .join(ProfileSkill.skill)
        .all()
    )

    baseline_profile_skills: List[Dict[str, Any]] = []
    for ps in db_profile_skills:
        baseline_profile_skills.append({
            "skill_id": ps.skill_id,
            "skill_name": ps.skill.canonical_name,
            "confidence": ps.confidence if ps.confidence is not None else "Medium",
        })

    # 4. Load resume sections for experience alignment
    resume = (
        db.query(Resume)
        .filter(Resume.profile_id == profile_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    resume_sections: Dict[str, str] = {}
    if resume and resume.sections:
        resume_sections = {s.section_type: s.text or "" for s in resume.sections}
    else:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if profile:
            if profile.experience_summary:
                resume_sections["experience"] = profile.experience_summary
            if profile.education_summary:
                resume_sections["education"] = profile.education_summary

    # 5. Load market demand score
    scores_file = PROJECT_ROOT / "data" / "processed" / "demand_scores.json"
    demand_scores = {}
    if scores_file.exists():
        try:
            with open(scores_file, "r", encoding="utf-8") as f:
                demand_scores = json.load(f)
        except Exception:
            demand_scores = {}
    market_demand = demand_scores.get(career.name, 0.5)

    # 6. Baseline calculations using exact scoring & gap functions
    base_fit = calculate_career_fit(
        profile_skills=baseline_profile_skills,
        career=career.name,
        resume_sections=resume_sections,
        market_demand=market_demand,
    )
    base_readiness = calculate_readiness(
        profile_skills=baseline_profile_skills,
        career_skills=career_skills_list,
        resume_sections=resume_sections,
        career_name=career.name,
    )
    base_gaps = get_skill_gaps(
        profile_skills=baseline_profile_skills,
        career_skills=career_skills_list,
    )
    base_missing_count = sum(1 for g in base_gaps if g.get("status") == "Missing")

    baseline_summary = {
        "career_fit_score": round(base_fit["total_score"], 2),
        "readiness": round(base_readiness, 2),
        "missing_skills_count": base_missing_count,
    }

    # 7. Create simulation state
    simulated_profile_skills = create_simulation_state(
        profile_skills=baseline_profile_skills,
        add_skills=add_skills,
        remove_skills=remove_skills,
    )

    # 8. Simulated calculations using EXACT SAME functions
    sim_fit = calculate_career_fit(
        profile_skills=simulated_profile_skills,
        career=career.name,
        resume_sections=resume_sections,
        market_demand=market_demand,
    )
    sim_readiness = calculate_readiness(
        profile_skills=simulated_profile_skills,
        career_skills=career_skills_list,
        resume_sections=resume_sections,
        career_name=career.name,
    )
    sim_gaps = get_skill_gaps(
        profile_skills=simulated_profile_skills,
        career_skills=career_skills_list,
    )
    sim_missing_count = sum(1 for g in sim_gaps if g.get("status") == "Missing")

    simulated_summary = {
        "career_fit_score": round(sim_fit["total_score"], 2),
        "readiness": round(sim_readiness, 2),
        "missing_skills_count": sim_missing_count,
    }

    # 9. Compute delta = simulated - baseline
    delta_summary = {
        "career_fit_score": round(
            simulated_summary["career_fit_score"] - baseline_summary["career_fit_score"],
            2,
        ),
        "readiness": round(
            simulated_summary["readiness"] - baseline_summary["readiness"],
            2,
        ),
        "missing_skills_count": (
            simulated_summary["missing_skills_count"]
            - baseline_summary["missing_skills_count"]
        ),
    }

    # 10. Persist to simulations, simulation_results, and simulation_changes
    sim_record = Simulation(
        profile_id=profile_id,
        career_id=career_id,
    )
    db.add(sim_record)
    db.flush()

    skills_cache = {s.canonical_name.lower(): s.id for s in db.query(Skill).all()}
    for a_skill in (add_skills or []):
        norm = normalize_skill(a_skill).lower()
        sk_id = skills_cache.get(a_skill.lower()) or skills_cache.get(norm)
        if sk_id:
            db.add(SimulationChange(simulation_id=sim_record.id, skill_id=sk_id, action="add"))

    for r_skill in (remove_skills or []):
        norm = normalize_skill(r_skill).lower()
        sk_id = skills_cache.get(r_skill.lower()) or skills_cache.get(norm)
        if sk_id:
            db.add(SimulationChange(simulation_id=sim_record.id, skill_id=sk_id, action="remove"))

    result_record = SimulationResult(
        simulation_id=sim_record.id,
        baseline=baseline_summary,
        simulated=simulated_summary,
        delta=delta_summary,
    )
    db.add(result_record)
    db.commit()

    return {
        "simulation_id": sim_record.id,
        "profile_id": str(profile_id),
        "career_id": career_id,
        "baseline": baseline_summary,
        "simulated": simulated_summary,
        "delta": delta_summary,
        "added_skills": list(add_skills or []),
        "removed_skills": list(remove_skills or []),
    }


def get_simulation_result(simulation_id: int, db: Session) -> Dict[str, Any]:
    """Retrieve full persisted simulation result by ID."""
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise ValueError(f"Simulation with id {simulation_id} not found")

    if not sim.results:
        raise ValueError(f"No results found for simulation {simulation_id}")

    added = [c.skill.canonical_name for c in sim.changes if c.action == "add"]
    removed = [c.skill.canonical_name for c in sim.changes if c.action == "remove"]

    return {
        "simulation_id": sim.id,
        "profile_id": str(sim.profile_id),
        "career_id": sim.career_id,
        "baseline": sim.results.baseline,
        "simulated": sim.results.simulated,
        "delta": sim.results.delta,
        "added_skills": added,
        "removed_skills": removed,
    }

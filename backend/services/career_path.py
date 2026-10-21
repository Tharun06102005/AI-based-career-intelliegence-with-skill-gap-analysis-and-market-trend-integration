"""Career Path progression service for AI Career Intelligence.

Defines 4-level career progression paths (Junior, Mid, Senior, Lead) for
the 10 canonical career roles and provides level assessment based on
candidate skills.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

# Configure backend directory on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.job_pipeline import normalize_job_title
from services.skill_normalizer import normalize_skill


class LevelInfo(dict):
    """Dictionary representing level requirements with list-like compatibility.

    Supports both dictionary access (`level["skills"]`, `level["experience"]`)
    and membership checks (`"Python" in level`, `for skill in level:`).
    """

    def __init__(self, skills: List[str], experience: str = ""):
        super().__init__(skills=skills, experience=experience)
        self.skills = skills
        self.experience = experience

    def __iter__(self):
        return iter(self.skills)

    def __contains__(self, item: Any) -> bool:
        return super().__contains__(item) or item in self.skills

    def __len__(self) -> int:
        return len(self.skills)


# Progression order for levels
LEVEL_ORDER: List[str] = ["Junior", "Mid", "Senior", "Lead"]

# Standard experience ranges per level
LEVEL_EXPERIENCE: Dict[str, str] = {
    "Junior": "0-2 yrs",
    "Mid": "2-5 yrs",
    "Senior": "5+ yrs",
    "Lead": "8+ yrs",
}

# Next level progression map
NEXT_LEVEL_MAP: Dict[str, str] = {
    "Junior": "Mid",
    "Mid": "Senior",
    "Senior": "Lead",
    "Lead": "Expert",
}

# Distance in levels from Lead role
LEVELS_AWAY_MAP: Dict[str, int] = {
    "Junior": 3,
    "Mid": 2,
    "Senior": 1,
    "Lead": 0,
}

# Threshold to qualify for a level (e.g. 60% of required skills)
QUALIFICATION_THRESHOLD: float = 60.0

# -----------------------------------------------------------------------------
# CAREER_PATHS defining progression for all 10 career roles
# -----------------------------------------------------------------------------
CAREER_PATHS: Dict[str, Dict[str, LevelInfo]] = {
    "Software Engineer": {
        "Junior": LevelInfo(
            skills=["Python", "JavaScript", "SQL", "Git", "HTML", "CSS"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Docker", "REST APIs", "React", "Testing", "CI/CD"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["System Design", "Kubernetes", "AWS", "Microservices"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Architecture", "Team Management", "Strategy"],
            experience="8+ yrs",
        ),
    },
    "Data Scientist": {
        "Junior": LevelInfo(
            skills=["Python", "SQL", "Pandas", "NumPy", "Statistics", "Excel"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Machine Learning", "Scikit-learn", "TensorFlow", "Visualization"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["Deep Learning", "MLOps", "PyTorch", "Research"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["AI Strategy", "Team Leadership", "Research Direction"],
            experience="8+ yrs",
        ),
    },
    "Machine Learning Engineer": {
        "Junior": LevelInfo(
            skills=["Python", "TensorFlow", "Pandas", "NumPy", "SQL"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["PyTorch", "Docker", "MLOps", "REST APIs", "CI/CD"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["Kubernetes", "AWS", "System Design", "Research"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["AI Architecture", "Team Leadership", "Strategy"],
            experience="8+ yrs",
        ),
    },
    "Backend Developer": {
        "Junior": LevelInfo(
            skills=["Python", "SQL", "REST APIs", "Git", "Linux"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Docker", "Redis", "PostgreSQL", "Testing", "CI/CD"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["Kubernetes", "AWS", "System Design", "Microservices"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Architecture", "Team Management", "Strategy"],
            experience="8+ yrs",
        ),
    },
    "Frontend Developer": {
        "Junior": LevelInfo(
            skills=["HTML", "CSS", "JavaScript", "React", "Git"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["TypeScript", "Next.js", "Testing", "REST APIs", "Bootstrap"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["System Design", "Performance", "CI/CD", "GraphQL"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Architecture", "Team Leadership", "Design Systems"],
            experience="8+ yrs",
        ),
    },
    "Full Stack Developer": {
        "Junior": LevelInfo(
            skills=["HTML", "CSS", "JavaScript", "Python", "SQL", "Git"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["React", "Node.js", "Docker", "REST APIs", "TypeScript"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["AWS", "System Design", "CI/CD", "Kubernetes"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Architecture", "Team Management", "Strategy"],
            experience="8+ yrs",
        ),
    },
    "DevOps Engineer": {
        "Junior": LevelInfo(
            skills=["Linux", "Git", "Docker", "Bash", "CI/CD"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Kubernetes", "AWS", "Terraform", "Ansible", "Prometheus"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["System Design", "Security", "Multi-cloud", "Grafana"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["DevOps Strategy", "Team Leadership", "Architecture"],
            experience="8+ yrs",
        ),
    },
    "Data Analyst": {
        "Junior": LevelInfo(
            skills=["SQL", "Excel", "Python", "Pandas", "Power BI"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Tableau", "Statistics", "Machine Learning", "NumPy"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["Data Strategy", "Advanced ML", "Leadership"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Analytics Strategy", "Team Management"],
            experience="8+ yrs",
        ),
    },
    "AI Engineer": {
        "Junior": LevelInfo(
            skills=["Python", "TensorFlow", "NLP", "OpenCV", "REST APIs"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["PyTorch", "LLM", "FastAPI", "Docker", "MLOps"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["System Design", "Kubernetes", "AWS", "Research"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["AI Strategy", "Team Leadership", "Architecture"],
            experience="8+ yrs",
        ),
    },
    "Cloud Engineer": {
        "Junior": LevelInfo(
            skills=["AWS", "Linux", "Docker", "Git", "Bash"],
            experience="0-2 yrs",
        ),
        "Mid": LevelInfo(
            skills=["Kubernetes", "Terraform", "CI/CD", "Azure", "GCP"],
            experience="2-5 yrs",
        ),
        "Senior": LevelInfo(
            skills=["Multi-cloud", "Security", "System Design", "Ansible"],
            experience="5+ yrs",
        ),
        "Lead": LevelInfo(
            skills=["Cloud Strategy", "Team Leadership", "Architecture"],
            experience="8+ yrs",
        ),
    },
}


def _extract_skill_set(skills_input: Any) -> Set[str]:
    """Extract and normalize a set of skill names from strings, dicts, or ORM models."""
    if not skills_input:
        return set()

    extracted: Set[str] = set()
    if isinstance(skills_input, (list, set, tuple)):
        for item in skills_input:
            if isinstance(item, str):
                extracted.add(item.strip())
            elif isinstance(item, dict):
                val = (
                    item.get("skill_name")
                    or item.get("skill")
                    or item.get("name")
                    or item.get("canonical_name")
                )
                if val:
                    extracted.add(str(val).strip())
            elif hasattr(item, "skill") and hasattr(item.skill, "canonical_name"):
                extracted.add(str(item.skill.canonical_name).strip())
            elif hasattr(item, "canonical_name"):
                extracted.add(str(item.canonical_name).strip())

    return extracted


def _is_skill_matched(required_skill: str, candidate_skills: Set[str]) -> bool:
    """Check if required_skill is present in candidate_skills using normalization & aliases."""
    if not required_skill:
        return False

    req_clean = required_skill.strip().lower()
    req_norm = normalize_skill(required_skill).strip().lower()

    for cand in candidate_skills:
        cand_clean = cand.strip().lower()
        if cand_clean == req_clean:
            return True
        if normalize_skill(cand).strip().lower() in (req_clean, req_norm):
            return True

    return False


def get_career_path(career_role: str) -> Dict[str, LevelInfo]:
    """Return the full career path progression for a given role.

    Parameters:
        career_role: Name of the career role (e.g. 'Software Engineer', 'Data Scientist').

    Returns:
        Dict mapping each level ('Junior', 'Mid', 'Senior', 'Lead') to its requirements.
    """
    if not career_role or not isinstance(career_role, str):
        raise ValueError("career_role must be a non-empty string.")

    # 1. Exact match lookup
    if career_role in CAREER_PATHS:
        return CAREER_PATHS[career_role]

    # 2. Canonical mapping lookup
    canonical = normalize_job_title(career_role)
    if canonical in CAREER_PATHS:
        return CAREER_PATHS[canonical]

    # 3. Case-insensitive lookup
    for name, path in CAREER_PATHS.items():
        if name.lower() == career_role.strip().lower():
            return path

    raise ValueError(
        f"Career path not found for role '{career_role}'. "
        f"Available roles: {list(CAREER_PATHS.keys())}"
    )


def get_current_level(
    profile_skills: Any,
    career_role: str,
) -> Dict[str, Any]:
    """Compare candidate profile skills against level requirements for a role.

    Parameters:
        profile_skills: Candidate skills (list of strings, dicts, or ORM models).
        career_role: Canonical or mapped career role name.

    Returns:
        Dict with keys:
        - current_level: 'Junior' | 'Mid' | 'Senior' | 'Lead'
        - current_level_match: float (0.0 - 100.0)
        - next_level: 'Mid' | 'Senior' | 'Lead' | 'Expert'
        - skills_to_advance: list of missing skills for next level
        - levels_away: int (0 to 3)
    """
    path = get_career_path(career_role)
    cand_skill_set = _extract_skill_set(profile_skills)

    # Calculate match percentage and matched skills for each level
    level_matches: Dict[str, Dict[str, Any]] = {}
    for level_name in LEVEL_ORDER:
        level_data = path[level_name]
        req_skills: List[str] = (
            level_data["skills"] if isinstance(level_data, dict) else list(level_data)
        )

        matched: List[str] = [
            s for s in req_skills if _is_skill_matched(s, cand_skill_set)
        ]
        missing: List[str] = [
            s for s in req_skills if not _is_skill_matched(s, cand_skill_set)
        ]

        total = len(req_skills)
        match_pct = round((len(matched) / total * 100.0), 2) if total > 0 else 0.0

        level_matches[level_name] = {
            "match_pct": match_pct,
            "matched_skills": matched,
            "missing_skills": missing,
            "total_skills": total,
        }

    # Determine current level by highest qualified level (>= QUALIFICATION_THRESHOLD)
    achieved_level = "Junior"
    for level_name in reversed(LEVEL_ORDER):
        if level_matches[level_name]["match_pct"] >= QUALIFICATION_THRESHOLD:
            achieved_level = level_name
            break

    # If achieved is Junior, current_level_match is Junior match %
    current_match = level_matches[achieved_level]["match_pct"]
    next_level = NEXT_LEVEL_MAP.get(achieved_level, "Expert")
    levels_away = LEVELS_AWAY_MAP.get(achieved_level, 0)

    # Skills to advance are missing skills of next level (empty if already Lead/Expert)
    if next_level != "Expert" and next_level in level_matches:
        skills_to_advance = level_matches[next_level]["missing_skills"]
    else:
        skills_to_advance = []

    return {
        "current_level": achieved_level,
        "current_level_match": current_match,
        "next_level": next_level,
        "skills_to_advance": skills_to_advance,
        "levels_away": levels_away,
    }


def get_all_paths() -> Dict[str, Dict[str, LevelInfo]]:
    """Return career paths for all 10 roles."""
    return CAREER_PATHS

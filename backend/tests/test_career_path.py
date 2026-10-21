"""Unit tests for the Career Path service and API endpoint."""

import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from services.career_path import (
    CAREER_PATHS,
    LEVEL_ORDER,
    get_all_paths,
    get_career_path,
    get_current_level,
)


def test_career_paths_completeness():
    """Verify all 10 roles are defined and have all 4 levels with skills."""
    expected_roles = [
        "Software Engineer",
        "Data Scientist",
        "Machine Learning Engineer",
        "Backend Developer",
        "Frontend Developer",
        "Full Stack Developer",
        "DevOps Engineer",
        "Data Analyst",
        "AI Engineer",
        "Cloud Engineer",
    ]
    all_paths = get_all_paths()
    assert len(all_paths) == 10

    for role in expected_roles:
        assert role in all_paths, f"Missing role: {role}"
        path = all_paths[role]
        for level in LEVEL_ORDER:
            assert level in path, f"Missing level {level} in {role}"
            level_info = path[level]
            assert "skills" in level_info
            assert len(level_info["skills"]) > 0
            assert "experience" in level_info


def test_level_info_compatibility():
    """Verify LevelInfo supports both dict and sequence access."""
    path = get_career_path("Software Engineer")
    junior = path["Junior"]

    # Dictionary access
    assert "Python" in junior["skills"]
    assert junior["experience"] == "0-2 yrs"

    # Membership check
    assert "Python" in junior
    assert "JavaScript" in junior
    assert "Rust" not in junior

    # Iterable behavior
    skills_list = list(junior)
    assert "Python" in skills_list
    assert len(junior) == 6


def test_get_current_level_junior():
    """Verify candidate with Junior skills is placed in Junior with Mid as next."""
    skills = ["Python", "JavaScript", "SQL", "Git", "HTML", "CSS"]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Junior"
    assert res["current_level_match"] == 100.0
    assert res["next_level"] == "Mid"
    assert res["levels_away"] == 3
    assert set(res["skills_to_advance"]) == {"Docker", "REST APIs", "React", "Testing", "CI/CD"}


def test_get_current_level_mid():
    """Verify candidate with Junior and Mid skills advances to Mid with Senior as next."""
    skills = [
        "Python", "JavaScript", "SQL", "Git", "HTML", "CSS",
        "Docker", "REST APIs", "React", "Testing", "CI/CD"
    ]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Mid"
    assert res["current_level_match"] == 100.0
    assert res["next_level"] == "Senior"
    assert res["levels_away"] == 2
    assert set(res["skills_to_advance"]) == {"System Design", "Kubernetes", "AWS", "Microservices"}


def test_get_current_level_senior():
    """Verify candidate with Senior skills is placed in Senior with Lead as next."""
    skills = [
        "System Design", "Kubernetes", "AWS", "Microservices"
    ]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Senior"
    assert res["current_level_match"] == 100.0
    assert res["next_level"] == "Lead"
    assert res["levels_away"] == 1
    assert set(res["skills_to_advance"]) == {"Architecture", "Team Management", "Strategy"}


def test_get_current_level_lead():
    """Verify candidate with Lead skills is placed in Lead with Expert as next."""
    skills = [
        "Architecture", "Team Management", "Strategy"
    ]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Lead"
    assert res["current_level_match"] == 100.0
    assert res["next_level"] == "Expert"
    assert res["levels_away"] == 0
    assert res["skills_to_advance"] == []


def test_get_current_level_partial_match():
    """Verify candidate with partial skills calculates correct percentage."""
    # 3 out of 6 Junior skills = 50%
    skills = ["Python", "JavaScript", "SQL"]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Junior"
    assert res["current_level_match"] == 50.0
    assert res["next_level"] == "Mid"
    assert res["levels_away"] == 3


def test_get_current_level_normalization_and_aliases():
    """Verify skill abbreviations like 'k8s' match 'Kubernetes'."""
    skills = ["k8s", "aws", "system design", "microservices"]
    res = get_current_level(skills, "Software Engineer")

    assert res["current_level"] == "Senior"
    assert res["current_level_match"] == 100.0

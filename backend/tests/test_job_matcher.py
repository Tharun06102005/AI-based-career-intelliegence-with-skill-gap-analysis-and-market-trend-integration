"""Automated test suite for Job & Internship Matching Engine."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from models.database import JobOpportunity
from services.job_matcher import calculate_opportunity_match, normalize_opportunity_url


def test_normalize_opportunity_url():
    """Verify URL deduplication cleaner strips tracking params and trailing slashes."""
    dirty_url = "https://example.com/jobs/view/123/?utm_source=linkedin&utm_medium=feed&ref=share/"
    cleaned = normalize_opportunity_url(dirty_url)
    assert cleaned == "https://example.com/jobs/view/123"

    url_2 = "https://Careers.Google.Com/Jobs/Swe/"
    assert normalize_opportunity_url(url_2) == "https://careers.google.com/jobs/swe"


def test_calculate_opportunity_match_with_verified_skills():
    """Verify opportunity match formula and bonus awarded for assessment-verified skills."""
    mock_job = JobOpportunity(
        title="Junior Backend Developer",
        company_name="Acme Corp",
        work_mode="Remote",
        experience_level="Junior",
        required_skills=["Python", "SQL", "Docker"],
        preferred_skills=["Redis", "PostgreSQL"],
    )

    # Candidate 1: Has skills, but unverified
    profile_skills_unverified = [
        {"skill_name": "Python", "is_verified": False, "confidence": 0.6},
        {"skill_name": "SQL", "is_verified": False, "confidence": 0.6},
        {"skill_name": "Docker", "is_verified": False, "confidence": 0.6},
    ]

    # Candidate 2: Has skills AND assessment-verified
    profile_skills_verified = [
        {"skill_name": "Python", "is_verified": True, "confidence": 0.9},
        {"skill_name": "SQL", "is_verified": True, "confidence": 0.9},
        {"skill_name": "Docker", "is_verified": True, "confidence": 0.9},
    ]

    res_unverified = calculate_opportunity_match(profile_skills_unverified, mock_job)
    res_verified = calculate_opportunity_match(profile_skills_verified, mock_job)

    assert res_unverified["match_score"] > 60.0
    # Candidate with verified skills must score higher than unverified candidate
    assert res_verified["match_score"] > res_unverified["match_score"]
    assert len(res_verified["verified_matched_skills"]) == 3
    assert len(res_unverified["verified_matched_skills"]) == 0

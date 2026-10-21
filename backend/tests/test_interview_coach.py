"""Automated test suite for AI Mock Interview Coach."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from services.interview_coach import FALLBACK_QUESTIONS


def test_interview_fallback_questions_available():
    """Verify fallback interview questions exist across canonical roles and categories."""
    assert "Software Engineer" in FALLBACK_QUESTIONS
    assert "technical" in FALLBACK_QUESTIONS["Software Engineer"]
    assert "project_defense" in FALLBACK_QUESTIONS["Software Engineer"]
    assert "hr" in FALLBACK_QUESTIONS["Software Engineer"]

    swe_tech = FALLBACK_QUESTIONS["Software Engineer"]["technical"]
    assert len(swe_tech) > 0
    assert "question" in swe_tech[0]

"""Automated test suite for Skill Verification and Adaptive Assessment Engine."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from services.code_executor import evaluate_test_cases, execute_python_code, scan_code_security
from services.assessment_engine import determine_next_difficulty


def test_code_executor_safe_execution():
    """Verify safe python code executes properly and returns standard output."""
    res = execute_python_code("print('Hello Career Intelligence')")
    assert res["success"] is True
    assert "Hello Career Intelligence" in res["stdout"]
    assert res["error"] is None


def test_code_executor_timeout():
    """Verify infinite loop triggers time limit exceeded without crashing."""
    res = execute_python_code("while True: pass", timeout_seconds=1.0)
    assert res["success"] is False
    assert "timed out" in res["stderr"].lower() or "time limit exceeded" in res["error"].lower()


def test_code_executor_security_violation():
    """Verify dangerous modules like socket, subprocess, os are intercepted."""
    vuln_code_1 = "import socket\ns = socket.socket()"
    vuln_code_2 = "import subprocess\nsubprocess.run(['ls'])"
    vuln_code_3 = "import os\nos.system('dir')"

    assert scan_code_security(vuln_code_1) is not None
    assert "socket" in scan_code_security(vuln_code_1)

    assert scan_code_security(vuln_code_2) is not None
    assert "subprocess" in scan_code_security(vuln_code_2)

    assert scan_code_security(vuln_code_3) is not None
    assert "system" in scan_code_security(vuln_code_3)


def test_evaluate_test_cases():
    """Verify test cases runner scores test inputs correctly."""
    user_code = (
        "def reverse_words(sentence: str) -> str:\n"
        "    return ' '.join(sentence.strip().split()[::-1])\n"
    )
    test_cases = [
        {"input": "'hello world'", "expected_output": "world hello", "is_hidden": False},
        {"input": "'fastapi python'", "expected_output": "python fastapi", "is_hidden": True},
    ]

    res = evaluate_test_cases(user_code, test_cases, function_name="reverse_words")
    assert res["all_passed"] is True
    assert res["passed_count"] == 2
    assert res["score_percentage"] == 100.0


def test_adaptive_difficulty_progression():
    """Verify adaptive algorithm increases difficulty on streaks and decreases on errors."""
    # Streak of 2 correct answers in Beginner -> Intermediate
    diff1 = determine_next_difficulty("Beginner", was_correct=True, recent_responses=[True, True])
    assert diff1 == "Intermediate"

    # Streak of 2 correct in Intermediate -> Advanced
    diff2 = determine_next_difficulty("Intermediate", was_correct=True, recent_responses=[True, True])
    assert diff2 == "Advanced"

    # Incorrect answer in Advanced -> Intermediate
    diff3 = determine_next_difficulty("Advanced", was_correct=False, recent_responses=[True, False])
    assert diff3 == "Intermediate"

    # Incorrect answer in Intermediate -> Beginner
    diff4 = determine_next_difficulty("Intermediate", was_correct=False, recent_responses=[False])
    assert diff4 == "Beginner"

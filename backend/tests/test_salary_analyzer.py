import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
import pytest

from services.salary_analyzer import (
    ANNUAL_WORK_HOURS,
    analyze_salary,
    clear_salary_cache,
    get_all_roles_salary_summary,
    load_salary_data,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure in-memory cache is cleared before and after tests."""
    clear_salary_cache()
    yield
    clear_salary_cache()


def test_analyze_salary_with_synthetic_data():
    """Verify statistical calculation with known values and hourly conversion."""
    data = {
        "job_id": [101, 102, 103, 104, 105],
        "title": [
            "Software Engineer",
            "Junior Software Engineer",
            "Senior Software Engineer",
            "SWE",
            "Staff Software Engineer",
        ],
        "normalized_role": [
            "Software Engineer",
            "Software Engineer",
            "Software Engineer",
            "Software Engineer",
            "Software Engineer",
        ],
        # Hourly ($50/hr * 2080 = $104,000)
        "min_salary": [50.0, 120000.0, 140000.0, None, 180000.0],
        "med_salary": [None, None, 150000.0, 160000.0, None],
        "max_salary": [50.0, 130000.0, 160000.0, None, 220000.0],
        "pay_period": ["HOURLY", "YEARLY", "YEARLY", "YEARLY", "YEARLY"],
        "currency": ["USD", "USD", "USD", "USD", "USD"],
    }
    df = pd.DataFrame(data)

    # Values annualized:
    # 101: 50 * 2080 = 104,000
    # 102: (120k + 130k)/2 = 125,000
    # 103: med = 150,000
    # 104: med = 160,000
    # 105: (180k + 220k)/2 = 200,000
    # Sorted: [104000, 125000, 150000, 160000, 200000]
    # Median: 150,000
    # Mean: (104 + 125 + 150 + 160 + 200) / 5 = 147,800
    # Min: 104,000
    # Max: 200,000

    result = analyze_salary("Software Engineer", df=df)

    assert result["career_role"] == "Software Engineer"
    assert result["sample_size"] == 5
    assert result["currency"] == "USD"
    assert result["median_salary"] == 150000.0
    assert result["mean_salary"] == 147800.0
    assert result["min_salary"] == 104000.0
    assert result["max_salary"] == 200000.0
    assert result["p25_salary"] == 125000.0
    assert result["p75_salary"] == 160000.0

    # Verify hourly equivalent
    assert result["hourly_equivalent"]["min"] == round(104000.0 / ANNUAL_WORK_HOURS, 2)
    assert result["hourly_equivalent"]["median"] == round(150000.0 / ANNUAL_WORK_HOURS, 2)
    assert result["hourly_equivalent"]["max"] == round(200000.0 / ANNUAL_WORK_HOURS, 2)

    # Verify pay periods breakdown
    assert result["pay_period_breakdown"] == {"HOURLY": 1, "YEARLY": 4}


def test_analyze_salary_unknown_role():
    """Verify unknown or unmatched role returns structured empty metrics."""
    df = pd.DataFrame({
        "job_id": [1],
        "title": ["Dentist"],
        "normalized_role": ["Other"],
        "min_salary": [100000.0],
        "max_salary": [120000.0],
        "med_salary": [110000.0],
        "pay_period": ["YEARLY"],
        "currency": ["USD"],
    })

    result = analyze_salary("Astrophysicist", df=df)
    assert result["sample_size"] == 0
    assert result["median_salary"] == 0.0
    assert result["confidence"] == "None"
    assert "No salary records found" in result["message"]


def test_analyze_salary_case_insensitivity():
    """Verify role name matching is case-insensitive and normalizes aliases."""
    data = {
        "job_id": [1, 2],
        "title": ["Software Engineer", "Backend Developer"],
        "normalized_role": ["Software Engineer", "Backend Developer"],
        "min_salary": [100000.0, 110000.0],
        "max_salary": [120000.0, 130000.0],
        "med_salary": [None, None],
        "pay_period": ["YEARLY", "YEARLY"],
        "currency": ["USD", "USD"],
    }
    df = pd.DataFrame(data)

    result_lower = analyze_salary("software engineer", df=df)
    assert result_lower["career_role"] == "Software Engineer"
    assert result_lower["sample_size"] == 1
    assert result_lower["median_salary"] == 110000.0

    result_alias = analyze_salary("swe", df=df)
    assert result_alias["career_role"] == "Software Engineer"
    assert result_alias["sample_size"] == 1


def test_get_all_roles_summary():
    """Verify summary generation across multiple roles."""
    data = {
        "job_id": [1, 2],
        "title": ["Software Engineer", "Data Scientist"],
        "normalized_role": ["Software Engineer", "Data Scientist"],
        "min_salary": [100000.0, 120000.0],
        "max_salary": [120000.0, 140000.0],
        "med_salary": [None, None],
        "pay_period": ["YEARLY", "YEARLY"],
        "currency": ["USD", "USD"],
    }
    df = pd.DataFrame(data)

    summary = get_all_roles_salary_summary(
        roles=["Software Engineer", "Data Scientist", "AI Engineer"],
        df=df,
    )
    assert "Software Engineer" in summary
    assert "Data Scientist" in summary
    assert "AI Engineer" in summary
    assert summary["Software Engineer"]["sample_size"] == 1
    assert summary["Data Scientist"]["sample_size"] == 1
    assert summary["AI Engineer"]["sample_size"] == 0

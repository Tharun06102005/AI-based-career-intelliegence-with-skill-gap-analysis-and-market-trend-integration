"""Salary Analyzer service for AI Career Intelligence.

Loads salary and job posting datasets, maps postings to canonical career roles,
annualizes hourly pay periods, and calculates statistical salary benchmarks
(min, max, median, mean, 25th percentile, 75th percentile, and sample size).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

# Configure path imports
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.job_pipeline import CANONICAL_ROLES, normalize_job_title

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Default dataset paths
DEFAULT_SALARIES_PATH = PROJECT_ROOT / "data" / "raw" / "jobs" / "salaries.csv"
DEFAULT_POSTINGS_PATH = PROJECT_ROOT / "data" / "raw" / "postings.csv"
DEFAULT_OUTPUT_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "salary_benchmarks.json"

# In-memory DataFrame cache to avoid re-reading large CSV files on every call
_SALARY_DATA_CACHE: Optional[pd.DataFrame] = None

# Hours worked per year for standard 40-hour work week (40 hrs * 52 weeks)
ANNUAL_WORK_HOURS: int = 2080


def _resolve_existing_path(path: Union[str, Path], fallback_paths: Optional[List[Path]] = None) -> Path:
    """Resolve a file path checking absolute, relative, and fallback locations."""
    p = Path(path)
    if p.exists():
        return p.resolve()

    # Check relative to cwd
    cwd_path = Path.cwd() / p
    if cwd_path.exists():
        return cwd_path.resolve()

    # Check relative to project root
    root_path = PROJECT_ROOT / p
    if root_path.exists():
        return root_path.resolve()

    if fallback_paths:
        for fb in fallback_paths:
            if fb.exists():
                return fb.resolve()

    raise FileNotFoundError(f"Required dataset file could not be found at: {path}")


def load_salary_data(
    salaries_path: Optional[Union[str, Path]] = None,
    postings_path: Optional[Union[str, Path]] = None,
    force_reload: bool = False,
) -> pd.DataFrame:
    """Load salaries.csv and join with postings.csv on job_id to get job titles.

    Parameters:
        salaries_path: Path to raw salaries.csv (default: data/raw/jobs/salaries.csv).
        postings_path: Path to postings.csv (default: data/raw/postings.csv).
        force_reload: If True, bypasses in-memory DataFrame cache.

    Returns:
        pd.DataFrame containing salary columns joined with job title and normalized career role.
    """
    global _SALARY_DATA_CACHE

    if not force_reload and _SALARY_DATA_CACHE is not None:
        return _SALARY_DATA_CACHE.copy()

    # 1. Resolve dataset file paths
    target_sal_path = _resolve_existing_path(
        salaries_path or DEFAULT_SALARIES_PATH,
        [Path("data/raw/jobs/salaries.csv"), BACKEND_DIR / "data" / "raw" / "jobs" / "salaries.csv"],
    )
    target_post_path = _resolve_existing_path(
        postings_path or DEFAULT_POSTINGS_PATH,
        [Path("data/raw/postings.csv"), BACKEND_DIR / "data" / "raw" / "postings.csv"],
    )

    logger.info("Loading salaries dataset from: %s", target_sal_path)
    # Expected columns: salary_id, job_id, max_salary, med_salary, min_salary, pay_period, currency, compensation_type
    salaries_df = pd.read_csv(target_sal_path, low_memory=False)

    logger.info("Loading job postings titles from: %s", target_post_path)
    # Load only job_id and title for high performance & minimal RAM footprint
    postings_df = pd.read_csv(target_post_path, usecols=["job_id", "title"], low_memory=False)

    # Deduplicate postings by job_id before join
    postings_df = postings_df.drop_duplicates(subset=["job_id"]).dropna(subset=["job_id"])

    # 2. Join salaries and postings on job_id
    logger.info("Joining salaries (%d rows) with postings on job_id...", len(salaries_df))
    merged_df = pd.merge(salaries_df, postings_df, on="job_id", how="inner")

    # 3. Normalize job titles to canonical career roles
    logger.info("Normalizing job titles to canonical career roles...")
    merged_df["title"] = merged_df["title"].fillna("").astype(str)
    merged_df["normalized_role"] = merged_df["title"].apply(normalize_job_title)

    # Cache result
    _SALARY_DATA_CACHE = merged_df
    logger.info("Successfully loaded and joined %d salary records.", len(merged_df))
    return _SALARY_DATA_CACHE.copy()


def clear_salary_cache() -> None:
    """Clear the in-memory salary dataset cache."""
    global _SALARY_DATA_CACHE
    _SALARY_DATA_CACHE = None


def analyze_salary(
    career_role: str,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Filter salaries by normalized career role, annualize hourly pay, and compute metrics.

    Calculates:
    - min_salary: Minimum annual salary
    - max_salary: Maximum annual salary
    - median_salary: Median annual salary (50th percentile)
    - mean_salary: Mean / average annual salary
    - p25_salary: 25th percentile annual salary
    - p75_salary: 75th percentile annual salary
    - sample_size: Total count of salary records analyzed
    - currency: Dominant currency (typically 'USD')
    - salary_range: Formatted salary range string (e.g. '$125,000 - $190,000')
    - hourly_equivalent: Estimated min, median, max hourly rates
    - pay_period_breakdown: Record counts by original pay_period

    Parameters:
        career_role: Target career role name (e.g. 'Software Engineer', 'Data Scientist').
        df: Optional pre-loaded DataFrame from load_salary_data(). If None, loads automatically.

    Returns:
        Dict[str, Any] containing statistical salary metrics and metadata.
    """
    if df is None:
        df = load_salary_data()

    if not career_role or not isinstance(career_role, str):
        raise ValueError("career_role must be a non-empty string.")

    # Determine canonical role matching the request
    normalized_input = normalize_job_title(career_role)
    target_role = normalized_input if normalized_input != "Other" else career_role.strip()

    # Filter dataframe by canonical role
    role_df = df[df["normalized_role"].str.lower() == target_role.lower()].copy()

    # If canonical filter returned nothing, attempt direct case-insensitive match on normalized_role or title
    if role_df.empty:
        role_df = df[df["normalized_role"].str.lower() == career_role.strip().lower()].copy()
    if role_df.empty:
        role_df = df[df["title"].str.lower().str.contains(career_role.strip().lower(), regex=False)].copy()

    # Pay period distribution before conversion
    pay_period_counts: Dict[str, int] = {}
    if not role_df.empty and "pay_period" in role_df.columns:
        pay_period_counts = (
            role_df["pay_period"].fillna("UNKNOWN").astype(str).str.upper().value_counts().to_dict()
        )

    # Empty result structure if no salary data found
    if role_df.empty:
        return {
            "career_role": target_role,
            "sample_size": 0,
            "currency": "USD",
            "min_salary": 0.0,
            "max_salary": 0.0,
            "median_salary": 0.0,
            "mean_salary": 0.0,
            "p25_salary": 0.0,
            "p75_salary": 0.0,
            "salary_range": "$0 - $0",
            "hourly_equivalent": {"min": 0.0, "median": 0.0, "max": 0.0},
            "pay_period_breakdown": {},
            "confidence": "None",
            "message": f"No salary records found for role '{career_role}'.",
        }

    # Ensure salary numeric columns exist and are numeric
    for col in ["min_salary", "med_salary", "max_salary"]:
        if col in role_df.columns:
            role_df[col] = pd.to_numeric(role_df[col], errors="coerce")
        else:
            role_df[col] = np.nan

    role_df["pay_period_clean"] = role_df["pay_period"].fillna("").astype(str).str.upper().str.strip()

    # -------------------------------------------------------------------------
    # Annualization:
    # Convert to annual salary if pay_period is HOURLY (multiply by 2080 for annual)
    # Also standardize MONTHLY (* 12), WEEKLY (* 52), BIWEEKLY (* 26)
    # -------------------------------------------------------------------------
    multipliers = {
        "HOURLY": ANNUAL_WORK_HOURS,  # 2080 hours
        "YEARLY": 1,
        "MONTHLY": 12,
        "WEEKLY": 52,
        "BIWEEKLY": 26,
    }

    # Vectorized multiplier mapping
    role_df["multiplier"] = role_df["pay_period_clean"].map(multipliers).fillna(1.0)

    # Annualize min, max, and med salaries
    role_df["annual_min"] = role_df["min_salary"] * role_df["multiplier"]
    role_df["annual_max"] = role_df["max_salary"] * role_df["multiplier"]
    role_df["annual_med"] = role_df["med_salary"] * role_df["multiplier"]

    # Calculate representative annual salary for each posting:
    # Priority: med_salary -> average of (min + max) -> min_salary -> max_salary
    midpoint = (role_df["annual_min"] + role_df["annual_max"]) / 2.0
    role_df["annual_rep"] = (
        role_df["annual_med"]
        .fillna(midpoint)
        .fillna(role_df["annual_min"])
        .fillna(role_df["annual_max"])
    )

    # Filter valid positive numbers
    valid_salaries = role_df["annual_rep"].dropna()
    valid_salaries = valid_salaries[valid_salaries > 0]

    # Handle anomalies / edge cases if any
    if len(valid_salaries) == 0:
        return {
            "career_role": target_role,
            "sample_size": 0,
            "currency": "USD",
            "min_salary": 0.0,
            "max_salary": 0.0,
            "median_salary": 0.0,
            "mean_salary": 0.0,
            "p25_salary": 0.0,
            "p75_salary": 0.0,
            "salary_range": "$0 - $0",
            "hourly_equivalent": {"min": 0.0, "median": 0.0, "max": 0.0},
            "pay_period_breakdown": pay_period_counts,
            "confidence": "None",
            "message": f"Salary records exist for '{career_role}' but contained no valid positive amounts.",
        }

    # Dominant currency (defaults to USD)
    currency = "USD"
    if "currency" in role_df.columns:
        currency_mode = role_df["currency"].dropna().mode()
        if not currency_mode.empty:
            currency = str(currency_mode.iloc[0]).upper()

    # -------------------------------------------------------------------------
    # Statistical Calculations:
    # -------------------------------------------------------------------------
    p25 = float(valid_salaries.quantile(0.25))
    median_val = float(valid_salaries.median())
    mean_val = float(valid_salaries.mean())
    p75 = float(valid_salaries.quantile(0.75))

    # Min and max: if sufficient samples, cap extreme zero-anomalies at 5th/95th or true valid min
    # We use min and max of valid salaries
    # If the raw min is unrealistically tiny (e.g. < 5,000 annual for professional tech roles),
    # use the 5th percentile as a sanitized lower bound while retaining true min in raw metrics
    raw_min = float(valid_salaries.min())
    raw_max = float(valid_salaries.max())

    if len(valid_salaries) >= 10 and raw_min < 15000:
        # Use 5th percentile to protect from stray $0 or unannualized data entry anomalies
        effective_min = float(valid_salaries.quantile(0.05))
    else:
        effective_min = raw_min

    if len(valid_salaries) >= 10 and raw_max > 1500000:
        # Protect from stray 100M data entry errors
        effective_max = float(valid_salaries.quantile(0.99))
    else:
        effective_max = raw_max

    sample_size = int(len(valid_salaries))

    # Determine confidence level based on sample size
    if sample_size >= 50:
        confidence = "High"
    elif sample_size >= 15:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Formatted range string (p25 to p75 interquartile or min to max)
    formatted_range = f"${effective_min:,.0f} - ${effective_max:,.0f}"

    return {
        "career_role": target_role,
        "sample_size": sample_size,
        "currency": currency,
        "min_salary": round(effective_min, 2),
        "max_salary": round(effective_max, 2),
        "median_salary": round(median_val, 2),
        "mean_salary": round(mean_val, 2),
        "p25_salary": round(p25, 2),
        "p75_salary": round(p75, 2),
        "salary_range": formatted_range,
        "hourly_equivalent": {
            "min": round(effective_min / ANNUAL_WORK_HOURS, 2),
            "median": round(median_val / ANNUAL_WORK_HOURS, 2),
            "max": round(effective_max / ANNUAL_WORK_HOURS, 2),
        },
        "pay_period_breakdown": pay_period_counts,
        "confidence": confidence,
    }


def get_all_roles_salary_summary(
    roles: Optional[List[str]] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Dict[str, Any]]:
    """Compute salary analytics across all canonical career roles.

    Parameters:
        roles: Optional custom list of roles (defaults to CANONICAL_ROLES).
        df: Optional pre-loaded DataFrame.

    Returns:
        Dict mapping career role name to its salary analytics dictionary.
    """
    if df is None:
        df = load_salary_data()

    target_roles = roles or CANONICAL_ROLES
    results: Dict[str, Dict[str, Any]] = {}

    for role in target_roles:
        results[role] = analyze_salary(role, df=df)

    return results


def save_salary_benchmarks(
    output_path: Optional[Union[str, Path]] = None,
    df: Optional[pd.DataFrame] = None,
) -> Path:
    """Compute benchmarks for all canonical roles and save to JSON.

    Parameters:
        output_path: Destination JSON path (default: data/processed/salary_benchmarks.json).
        df: Optional pre-loaded DataFrame.

    Returns:
        Path to the saved JSON file.
    """
    out = Path(output_path or DEFAULT_OUTPUT_JSON_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Computing salary benchmarks for all canonical roles...")
    summary = get_all_roles_salary_summary(df=df)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Saved salary benchmarks to: %s", out)
    return out


# =============================================================================
# CLI Entrypoint
# =============================================================================
def main() -> None:
    """Command-line interface for testing and running salary analysis."""
    parser = argparse.ArgumentParser(description="Salary Analyzer for AI Career Intelligence.")
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="Analyze a specific career role (e.g. 'Software Engineer').",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all canonical career roles and display summary table.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save benchmarks for all roles to data/processed/salary_benchmarks.json.",
    )
    parser.add_argument(
        "--salaries-csv",
        type=str,
        default=None,
        help="Custom path to salaries.csv",
    )
    parser.add_argument(
        "--postings-csv",
        type=str,
        default=None,
        help="Custom path to postings.csv",
    )

    args = parser.parse_args()

    # Load dataset once
    df = load_salary_data(
        salaries_path=args.salaries_csv,
        postings_path=args.postings_csv,
    )

    if args.role:
        metrics = analyze_salary(args.role, df=df)
        print(f"\nSalary Analysis for: {metrics['career_role']}")
        print("=" * 60)
        print(f"Sample Size:   {metrics['sample_size']} postings")
        print(f"Confidence:    {metrics['confidence']}")
        print(f"Median Salary: ${metrics['median_salary']:,.2f} {metrics['currency']}")
        print(f"Mean Salary:   ${metrics['mean_salary']:,.2f} {metrics['currency']}")
        print(f"Salary Range:  ${metrics['min_salary']:,.2f} - ${metrics['max_salary']:,.2f}")
        print(f"25th - 75th:   ${metrics['p25_salary']:,.2f} - ${metrics['p75_salary']:,.2f}")
        print(
            f"Hourly Equiv:  ${metrics['hourly_equivalent']['min']:.2f}/hr - "
            f"${metrics['hourly_equivalent']['max']:.2f}/hr "
            f"(Median: ${metrics['hourly_equivalent']['median']:.2f}/hr)"
        )
        print(f"Pay Periods:   {metrics['pay_period_breakdown']}")
        return

    if args.save:
        out_file = save_salary_benchmarks(df=df)
        print(f"[+] Successfully exported salary benchmarks to {out_file}")
        return

    # Default action or --all: Print summary table
    summary = get_all_roles_salary_summary(df=df)
    print("\n" + "=" * 90)
    print(f"{'Role':<26} | {'Count':<6} | {'25th Pct':<11} | {'Median':<11} | {'Mean':<11} | {'75th Pct':<11}")
    print("-" * 90)
    for role_name, data in summary.items():
        if data["sample_size"] > 0:
            print(
                f"{role_name:<26} | "
                f"{data['sample_size']:<6} | "
                f"${data['p25_salary']:<10,.0f} | "
                f"${data['median_salary']:<10,.0f} | "
                f"${data['mean_salary']:<10,.0f} | "
                f"${data['p75_salary']:<10,.0f}"
            )
        else:
            print(f"{role_name:<26} | {0:<6} | {'N/A':<11} | {'N/A':<11} | {'N/A':<11} | {'N/A':<11}")
    print("=" * 90)


if __name__ == "__main__":
    main()

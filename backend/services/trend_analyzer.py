"""Skill Trend Analyzer service for AI Career Intelligence.

Analyzes market demand and skill occurrences across processed job postings
to identify Hot, Rising, Stable, and Declining skills overall and by career role.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# Configure path imports
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.job_pipeline import normalize_job_title
from services.skill_normalizer import normalize_skill

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Default dataset paths
DEFAULT_PROCESSED_JOBS_PATH = PROJECT_ROOT / "data" / "processed" / "jobs_processed.csv"
DEFAULT_DEMAND_SCORES_PATH = PROJECT_ROOT / "data" / "processed" / "demand_scores.json"

# In-memory caches
_PROCESSED_JOBS_CACHE: Optional[pd.DataFrame] = None
_DEMAND_SCORES_CACHE: Optional[Dict[str, float]] = None


def _resolve_existing_path(path: Union[str, Path], fallback_paths: Optional[List[Path]] = None) -> Path:
    """Resolve a file path checking absolute, relative, and fallback locations."""
    p = Path(path)
    if p.exists():
        return p.resolve()

    cwd_path = Path.cwd() / p
    if cwd_path.exists():
        return cwd_path.resolve()

    root_path = PROJECT_ROOT / p
    if root_path.exists():
        return root_path.resolve()

    if fallback_paths:
        for fb in fallback_paths:
            if fb.exists():
                return fb.resolve()

    raise FileNotFoundError(f"Required dataset file could not be found at: {path}")


def load_processed_jobs(
    csv_path: Optional[Union[str, Path]] = None,
    force_reload: bool = False,
) -> pd.DataFrame:
    """Load data/processed/jobs_processed.csv into a pandas DataFrame.

    Parameters:
        csv_path: Path to processed jobs CSV (default: data/processed/jobs_processed.csv).
        force_reload: If True, reloads from disk bypassing memory cache.

    Returns:
        pd.DataFrame containing processed jobs with columns normalized_role and skills.
    """
    global _PROCESSED_JOBS_CACHE

    if not force_reload and _PROCESSED_JOBS_CACHE is not None:
        return _PROCESSED_JOBS_CACHE.copy()

    target_path = _resolve_existing_path(
        csv_path or DEFAULT_PROCESSED_JOBS_PATH,
        [
            Path("data/processed/jobs_processed.csv"),
            BACKEND_DIR / "data" / "processed" / "jobs_processed.csv",
        ],
    )

    logger.info("Loading processed jobs dataset from: %s", target_path)
    # Read relevant columns to keep memory usage low and execution fast
    df = pd.read_csv(
        target_path,
        usecols=lambda col: col in ["job_id", "title", "normalized_role", "skills"],
        low_memory=False,
    )

    _PROCESSED_JOBS_CACHE = df
    return _PROCESSED_JOBS_CACHE.copy()


def load_demand_scores(
    json_path: Optional[Union[str, Path]] = None,
    force_reload: bool = False,
) -> Dict[str, float]:
    """Load precomputed market demand scores from data/processed/demand_scores.json."""
    global _DEMAND_SCORES_CACHE

    if not force_reload and _DEMAND_SCORES_CACHE is not None:
        return dict(_DEMAND_SCORES_CACHE)

    target_path = _resolve_existing_path(
        json_path or DEFAULT_DEMAND_SCORES_PATH,
        [
            Path("data/processed/demand_scores.json"),
            BACKEND_DIR / "data" / "processed" / "demand_scores.json",
        ],
    )

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            _DEMAND_SCORES_CACHE = json.load(f)
    except Exception as exc:
        logger.warning("Could not read demand scores from %s: %s", target_path, exc)
        _DEMAND_SCORES_CACHE = {}

    return dict(_DEMAND_SCORES_CACHE)


def clear_trend_cache() -> None:
    """Clear in-memory processed jobs and demand scores caches."""
    global _PROCESSED_JOBS_CACHE, _DEMAND_SCORES_CACHE
    _PROCESSED_JOBS_CACHE = None
    _DEMAND_SCORES_CACHE = None


def get_trend_label(trend_score: float) -> str:
    """Classify trend score into human-readable label with emoji.

    Criteria:
    - trend_score > 0.7  → "Hot 🔥"
    - trend_score > 0.4  → "Rising ⬆️"
    - trend_score > 0.2  → "Stable ➡️"
    - below 0.2          → "Declining ⬇️"
    """
    if trend_score > 0.7:
        return "Hot 🔥"
    elif trend_score > 0.4:
        return "Rising ⬆️"
    elif trend_score > 0.2:
        return "Stable ➡️"
    else:
        return "Declining ⬇️"


def analyze_skill_trends(
    df: Optional[pd.DataFrame] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Count how many jobs mention each skill and calculate trend metrics.

    Parameters:
        df: Optional DataFrame (if None, loads from load_processed_jobs()).
        limit: Maximum number of top skills to return (default 20).

    Returns:
        List of dicts sorted by frequency descending:
        [
            {
                "skill": "Python",
                "job_count": 1200,
                "trend_score": 0.87,
                "trend_label": "Hot 🔥"
            },
            ...
        ]
    """
    if df is None:
        df = load_processed_jobs()

    if df.empty or "skills" not in df.columns:
        return []

    # Filter postings that have extracted skills
    valid_jobs = df[df["skills"].notnull()].copy()
    total_jobs = len(valid_jobs)

    if total_jobs == 0:
        return []

    # Count occurrences of each unique skill across postings
    skill_counts: Counter[str] = Counter()
    for raw_skills in valid_jobs["skills"]:
        if not isinstance(raw_skills, str):
            continue
        # Deduplicate per posting so each job counts at most once per skill
        seen_in_job = set()
        for item in raw_skills.split(";"):
            cleaned = item.strip()
            if cleaned and cleaned not in seen_in_job:
                seen_in_job.add(cleaned)
                skill_counts[cleaned] += 1

    # Format sorted results
    results: List[Dict[str, Any]] = []
    for skill_name, count in skill_counts.most_common(limit):
        trend_score = round(count / total_jobs, 2)
        results.append({
            "skill": skill_name,
            "job_count": int(count),
            "trend_score": float(trend_score),
            "trend_label": get_trend_label(trend_score),
        })

    return results


def get_trending_skills(
    career_role: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Get trending skills overall or filtered for a specific career role.

    Parameters:
        career_role: If provided, filters skills relevant to that role.
                     If None, returns overall top 20 trending skills.
        df: Optional preloaded DataFrame.
        limit: Number of top skills to return (default 20).

    Returns:
        List of skill trend dictionaries.
    """
    if df is None:
        df = load_processed_jobs()

    if not career_role:
        return analyze_skill_trends(df=df, limit=limit)

    # Normalize role name
    target_role = normalize_job_title(career_role)
    if target_role == "Other":
        target_role = career_role.strip()

    # Filter by normalized_role (case-insensitive)
    role_df = df[df["normalized_role"].str.lower() == target_role.lower()].copy()

    # If canonical filter returned no rows, fallback to matching on title substring
    if role_df.empty and "title" in df.columns:
        role_df = df[df["title"].str.lower().str.contains(career_role.strip().lower(), regex=False)].copy()

    return analyze_skill_trends(df=role_df, limit=limit)


def get_skill_trend(
    skill_name: str,
    career_role: Optional[str] = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Return trend data for a specific skill.

    Parameters:
        skill_name: Name of the skill (e.g. 'Python', 'Docker', 'AWS').
        career_role: Optional career role filter.
        df: Optional preloaded DataFrame.

    Returns:
        Dict containing skill, job_count, trend_score, and trend_label.
    """
    if not skill_name or not isinstance(skill_name, str):
        raise ValueError("skill_name must be a non-empty string.")

    if df is None:
        df = load_processed_jobs()

    # Optionally filter by role
    if career_role:
        target_role = normalize_job_title(career_role)
        if target_role == "Other":
            target_role = career_role.strip()
        role_df = df[df["normalized_role"].str.lower() == target_role.lower()].copy()
        if not role_df.empty:
            df = role_df

    valid_jobs = df[df["skills"].notnull()].copy()
    total_jobs = len(valid_jobs)

    if total_jobs == 0:
        return {
            "skill": skill_name,
            "job_count": 0,
            "trend_score": 0.0,
            "trend_label": get_trend_label(0.0),
        }

    target_clean = skill_name.strip().lower()
    target_norm = normalize_skill(skill_name).strip().lower()

    count = 0
    canonical_display_name = skill_name.strip()

    for raw_skills in valid_jobs["skills"]:
        if not isinstance(raw_skills, str):
            continue
        matched_in_job = False
        for item in raw_skills.split(";"):
            item_clean = item.strip().lower()
            if item_clean == target_clean or normalize_skill(item).strip().lower() in (target_clean, target_norm):
                matched_in_job = True
                canonical_display_name = item.strip()
                break
        if matched_in_job:
            count += 1

    trend_score = round(count / total_jobs, 2)
    return {
        "skill": canonical_display_name,
        "job_count": int(count),
        "trend_score": float(trend_score),
        "trend_label": get_trend_label(trend_score),
    }


# =============================================================================
# CLI Entrypoint
# =============================================================================
def main() -> None:
    """CLI to inspect and test skill trends."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    import argparse

    parser = argparse.ArgumentParser(description="Skill Trend Analyzer for AI Career Intelligence.")
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="Filter trending skills by career role (e.g. 'Software Engineer').",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Inspect trend metrics for a specific skill (e.g. 'Python').",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of skills to display (default 20).",
    )
    args = parser.parse_args()

    if args.skill:
        trend = get_skill_trend(args.skill, career_role=args.role)
        print(f"\nSkill Trend: {trend['skill']}")
        print("=" * 45)
        print(f"Job Count:   {trend['job_count']}")
        print(f"Trend Score: {trend['trend_score']:.2f}")
        print(f"Trend Label: {trend['trend_label']}")
        return

    trends = get_trending_skills(career_role=args.role, limit=args.limit)
    header = f"Top {len(trends)} Trending Skills"
    if args.role:
        header += f" for {args.role}"
    print("\n" + "=" * 65)
    print(header)
    print("=" * 65)
    print(f"{'Rank':<5} | {'Skill':<25} | {'Jobs':<7} | {'Score':<7} | {'Trend'}")
    print("-" * 65)
    for idx, item in enumerate(trends, start=1):
        print(
            f"{idx:<5} | "
            f"{item['skill']:<25} | "
            f"{item['job_count']:<7} | "
            f"{item['trend_score']:<7.2f} | "
            f"{item['trend_label']}"
        )
    print("=" * 65)


if __name__ == "__main__":
    main()

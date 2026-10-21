"""Job Market Data Pipeline service.

Loads raw LinkedIn job postings, cleans the dataset, normalizes job titles to
canonical career roles, extracts required technical skills using SKILL_PATTERNS,
and computes weighted market demand scores.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

# Ensure backend directory is in sys.path for direct or module execution
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.skill_extractor import SKILL_PATTERNS, extract_skills_from_text

# Default path to raw postings dataset
DEFAULT_RAW_CSV_PATH = BACKEND_DIR.parent / "data" / "raw" / "postings.csv"

# Exact target columns required from the raw postings dataset
REQUIRED_JOB_COLUMNS = [
    "job_id",
    "title",
    "company_name",
    "description",
    "location",
    "formatted_experience_level",
]

# Canonical career roles tracked by the system
CANONICAL_ROLES: List[str] = [
    "Software Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "DevOps Engineer",
    "Data Analyst",
    "Product Manager",
    "AI Engineer",
    "Cloud Engineer",
]

# Direct mappings for canonical titles and common abbreviations
EXACT_TITLE_MAPPINGS: Dict[str, str] = {
    "software engineer": "Software Engineer",
    "swe": "Software Engineer",
    "sde": "Software Engineer",
    "software developer": "Software Engineer",
    "data scientist": "Data Scientist",
    "ml engineer": "Machine Learning Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "backend developer": "Backend Developer",
    "backend engineer": "Backend Developer",
    "back end developer": "Backend Developer",
    "back-end developer": "Backend Developer",
    "frontend developer": "Frontend Developer",
    "frontend engineer": "Frontend Developer",
    "front end developer": "Frontend Developer",
    "front-end developer": "Frontend Developer",
    "full stack developer": "Full Stack Developer",
    "full stack engineer": "Full Stack Developer",
    "fullstack developer": "Full Stack Developer",
    "fullstack engineer": "Full Stack Developer",
    "full-stack developer": "Full Stack Developer",
    "devops engineer": "DevOps Engineer",
    "devops": "DevOps Engineer",
    "data analyst": "Data Analyst",
    "product manager": "Product Manager",
    "ai engineer": "AI Engineer",
    "cloud engineer": "Cloud Engineer",
}

# Regex patterns for matching job titles in order of specificity
ROLE_REGEX_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    (
        "Machine Learning Engineer",
        re.compile(r"\b(machine\s+learning\s+engineer|ml\s+engineer|machine\s+learning)\b", re.IGNORECASE),
    ),
    (
        "AI Engineer",
        re.compile(r"\b(ai\s+engineer|artificial\s+intelligence\s+engineer|genai\s+engineer)\b", re.IGNORECASE),
    ),
    (
        "Full Stack Developer",
        re.compile(
            r"\b(full[\s-]?stack\s+(developer|engineer|software)|fullstack\s*(developer|engineer)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Backend Developer",
        re.compile(
            r"\b(back[\s-]?end\s+(developer|engineer|software)|backend\s*(developer|engineer)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Frontend Developer",
        re.compile(
            r"\b(front[\s-]?end\s+(developer|engineer|software)|frontend\s*(developer|engineer)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "DevOps Engineer",
        re.compile(r"\b(devops(\s+engineer)?|site\s+reliability\s+engineer|sre)\b", re.IGNORECASE),
    ),
    (
        "Cloud Engineer",
        re.compile(r"\b(cloud\s+(engineer|architect|infrastructure\s+engineer))\b", re.IGNORECASE),
    ),
    (
        "Data Scientist",
        re.compile(r"\b(data\s+scientist|data\s+science)\b", re.IGNORECASE),
    ),
    (
        "Data Analyst",
        re.compile(r"\b(data\s+analyst|data\s+analytics|bi\s+analyst|business\s+intelligence\s+analyst)\b", re.IGNORECASE),
    ),
    (
        "Product Manager",
        re.compile(r"\b(product\s+manager|technical\s+product\s+manager|associate\s+product\s+manager)\b", re.IGNORECASE),
    ),
    (
        "Software Engineer",
        re.compile(
            r"\b(software\s+engineer|software\s+developer|software\s+development\s+engineer|swe|sde)\b",
            re.IGNORECASE,
        ),
    ),
]


def load_raw_jobs(csv_path: Union[str, Path, None] = None, **kwargs) -> pd.DataFrame:
    """Load raw job postings from CSV using pandas.

    Returns a DataFrame containing the columns:
    job_id, title, company_name, description, location, formatted_experience_level.
    """
    if csv_path is None:
        target_path = DEFAULT_RAW_CSV_PATH
    else:
        target_path = Path(csv_path)

    if not target_path.exists():
        # Check relative to working directory or project root
        alt_path = Path.cwd() / target_path
        if alt_path.exists():
            target_path = alt_path
        else:
            raise FileNotFoundError(f"Raw jobs CSV file not found at: {target_path}")

    df = pd.read_csv(
        target_path,
        usecols=lambda col: col in REQUIRED_JOB_COLUMNS,
        low_memory=False,
        **kwargs,
    )

    # Ensure all required columns are present in the returned DataFrame
    for col in REQUIRED_JOB_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df[REQUIRED_JOB_COLUMNS]


def clean_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw job postings DataFrame.

    - Removes duplicate rows based on job_id.
    - Drops rows where title or description is null or empty.
    - Normalizes excessive whitespace in title and description.
    - Returns the cleaned DataFrame with reset index.
    """
    cleaned = df.copy()

    # 1. Remove duplicate job_ids
    cleaned = cleaned.drop_duplicates(subset=["job_id"])

    # 2. Drop rows where title or description is null
    cleaned = cleaned.dropna(subset=["title", "description"])

    # 3. Normalize whitespace in title and description
    cleaned["title"] = (
        cleaned["title"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    cleaned["description"] = (
        cleaned["description"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # Drop any rows that became empty strings after strip
    cleaned = cleaned[(cleaned["title"] != "") & (cleaned["description"] != "")]

    return cleaned.reset_index(drop=True)


def normalize_job_title(title: Union[str, None]) -> str:
    """Map raw job titles to canonical career roles.

    Mappings include:
    - "Software Engineer" / "SWE" -> "Software Engineer"
    - "Data Scientist" -> "Data Scientist"
    - "ML Engineer" -> "Machine Learning Engineer"
    - "Backend Developer" -> "Backend Developer"
    - "Frontend Developer" -> "Frontend Developer"
    - "Full Stack Developer" -> "Full Stack Developer"
    - "DevOps Engineer" -> "DevOps Engineer"
    - "Data Analyst" -> "Data Analyst"
    - "Product Manager" -> "Product Manager"
    - "AI Engineer" -> "AI Engineer"
    - "Cloud Engineer" -> "Cloud Engineer"

    Returns the canonical role name or "Other" if no match.
    """
    if not title or not isinstance(title, str):
        return "Other"

    stripped = title.strip()
    lower_title = stripped.lower()

    # Direct exact lookup
    if lower_title in EXACT_TITLE_MAPPINGS:
        return EXACT_TITLE_MAPPINGS[lower_title]

    # Pattern based classification
    for canonical_name, pattern in ROLE_REGEX_PATTERNS:
        if pattern.search(stripped):
            return canonical_name

    return "Other"


def extract_skills_from_description(description: Union[str, None]) -> List[str]:
    """Extract skills from a job description reusing skill_extractor.py.

    Matches text against SKILL_PATTERNS and returns an ordered list of unique
    canonical skill names found.
    """
    if not description or not isinstance(description, str):
        return []

    hits = extract_skills_from_text(description, "description")
    skills: List[str] = []
    seen = set()

    for hit in hits:
        skill_name = hit.get("skill_name")
        if skill_name and skill_name not in seen:
            seen.add(skill_name)
            skills.append(skill_name)

    return skills


def calculate_demand_score(role: str, jobs_df: pd.DataFrame) -> float:
    """Calculate the market demand score for a given canonical career role.

    Formula:
        DemandScore = 0.50 * normalized_job_count
                    + 0.25 * normalized_recent_job_count
                    + 0.15 * normalized_skill_frequency
                    + 0.10 * geographic_coverage

    All components are normalized to [0, 1].
    Returns a float between 0.0 and 1.0.
    """
    if jobs_df is None or len(jobs_df) == 0:
        return 0.0

    # Ensure normalized_role exists
    if "normalized_role" not in jobs_df.columns:
        if "title" in jobs_df.columns:
            jobs_df = jobs_df.copy()
            jobs_df["normalized_role"] = jobs_df["title"].apply(normalize_job_title)
        else:
            return 0.0

    role_jobs = jobs_df[jobs_df["normalized_role"] == role]
    role_count = len(role_jobs)

    if role_count == 0:
        return 0.0

    # 1. normalized_job_count (0.50)
    role_counts = jobs_df["normalized_role"].value_counts()
    non_other_counts = [cnt for r, cnt in role_counts.items() if r != "Other"]
    max_job_count = max(non_other_counts) if non_other_counts else max(role_counts.values, default=1)
    norm_job_count = min(1.0, max(0.0, role_count / max_job_count)) if max_job_count > 0 else 0.0

    # 2. normalized_recent_job_count (0.25)
    # Estimate recency using listed_time if available, or upper quantile of job_ids / index
    if "listed_time" in jobs_df.columns and jobs_df["listed_time"].notna().any():
        recent_thresh = jobs_df["listed_time"].quantile(0.70)
        recent_pool = jobs_df[jobs_df["listed_time"] >= recent_thresh]
    elif "job_id" in jobs_df.columns and pd.api.types.is_numeric_dtype(jobs_df["job_id"]):
        recent_thresh = jobs_df["job_id"].quantile(0.70)
        recent_pool = jobs_df[jobs_df["job_id"] >= recent_thresh]
    else:
        recent_pool = jobs_df.iloc[int(len(jobs_df) * 0.70) :]

    recent_role_jobs = recent_pool[recent_pool["normalized_role"] == role]
    recent_role_count = len(recent_role_jobs)
    recent_role_counts = recent_pool["normalized_role"].value_counts()
    non_other_recent = [cnt for r, cnt in recent_role_counts.items() if r != "Other"]
    max_recent_count = max(non_other_recent) if non_other_recent else max(recent_role_counts.values, default=1)
    norm_recent_count = min(1.0, max(0.0, recent_role_count / max_recent_count)) if max_recent_count > 0 else 0.0

    # 3. normalized_skill_frequency (0.15)
    # Average skills per posting for this role relative to maximum average
    if "skills" in role_jobs.columns:
        skill_counts = role_jobs["skills"].apply(lambda s: len(s) if isinstance(s, (list, set, tuple)) else 0)
    else:
        skill_counts = role_jobs["description"].apply(extract_skills_from_description).apply(len)

    avg_skills_role = float(skill_counts.mean()) if len(skill_counts) > 0 else 0.0

    # Find max avg skills across career roles for normalization benchmark
    max_avg_skills = 0.0
    for r in role_counts.index:
        if r == "Other":
            continue
        sub = jobs_df[jobs_df["normalized_role"] == r]
        if "skills" in sub.columns:
            cnts = sub["skills"].apply(lambda s: len(s) if isinstance(s, (list, set, tuple)) else 0)
        else:
            cnts = sub["description"].head(25).apply(extract_skills_from_description).apply(len)
        m = float(cnts.mean()) if len(cnts) > 0 else 0.0
        if m > max_avg_skills:
            max_avg_skills = m

    if max_avg_skills == 0.0:
        max_avg_skills = max(avg_skills_role, 8.0)

    norm_skill_freq = min(1.0, max(0.0, avg_skills_role / max_avg_skills)) if max_avg_skills > 0 else 0.0

    # 4. geographic_coverage (0.10)
    if "location" in jobs_df.columns:
        total_unique_locations = jobs_df["location"].dropna().nunique()
        role_unique_locations = role_jobs["location"].dropna().nunique()
        geo_coverage = role_unique_locations / total_unique_locations if total_unique_locations > 0 else 0.0
    else:
        geo_coverage = 0.0

    norm_geo_coverage = min(1.0, max(0.0, geo_coverage))

    # Calculate final weighted score
    demand_score = (
        0.50 * norm_job_count
        + 0.25 * norm_recent_count
        + 0.15 * norm_skill_freq
        + 0.10 * norm_geo_coverage
    )

    return round(float(min(1.0, max(0.0, demand_score))), 4)


def run_pipeline(
    csv_path: Union[str, Path, None] = None,
    return_df: bool = False,
) -> Union[Dict[str, float], Tuple[Dict[str, float], pd.DataFrame]]:
    """Execute the end-to-end job market data pipeline.

    Flow:
        load -> clean -> normalize -> extract skills -> calculate demand scores

    Returns:
        dict of {career_role: demand_score} (or tuple of (scores, df) if return_df=True).
    """
    resolved_path = csv_path or DEFAULT_RAW_CSV_PATH
    print(f"[Pipeline] Step 1/4: Loading raw jobs from '{resolved_path}'...")
    df = load_raw_jobs(resolved_path)
    print(f"[Pipeline] Loaded {len(df):,} job records.")

    print("[Pipeline] Step 2/4: Cleaning job postings (deduplication & whitespace)...")
    cleaned_df = clean_jobs(df)
    print(f"[Pipeline] Cleaned job postings count: {len(cleaned_df):,}")

    print("[Pipeline] Step 3/4: Normalizing job titles into canonical roles...")
    cleaned_df["normalized_role"] = cleaned_df["title"].apply(normalize_job_title)
    role_dist = cleaned_df["normalized_role"].value_counts().to_dict()
    print(f"[Pipeline] Found roles distribution (top 6): {dict(list(role_dist.items())[:6])}")

    print("[Pipeline] Step 4/4: Extracting technical skills from descriptions...")
    # Initialize empty skills list for all rows
    cleaned_df["skills"] = [[] for _ in range(len(cleaned_df))]
    # Optimize extraction by processing non-Other roles
    matched_mask = cleaned_df["normalized_role"] != "Other"
    matched_indices = cleaned_df[matched_mask].index
    print(f"[Pipeline] Extracting skills for {len(matched_indices):,} matched career role postings...")
    cleaned_df.loc[matched_indices, "skills"] = cleaned_df.loc[
        matched_indices, "description"
    ].apply(extract_skills_from_description)

    print("[Pipeline] Calculating market demand scores for canonical career roles...")
    demand_scores: Dict[str, float] = {}
    for role in CANONICAL_ROLES:
        score = calculate_demand_score(role, cleaned_df)
        demand_scores[role] = score
        count = len(cleaned_df[cleaned_df["normalized_role"] == role])
        print(f"  - {role:<26}: Demand Score = {score:.4f} (Jobs: {count:,})")

    print("[Pipeline] Pipeline execution completed successfully.")

    if return_df:
        return demand_scores, cleaned_df
    return demand_scores


if __name__ == "__main__":
    scores = run_pipeline()
    print("\nFinal Demand Scores:")
    for role, score in scores.items():
        print(f"  {role}: {score}")

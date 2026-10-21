"""Career Scoring Engine.

CRITICAL RULE:
    This scoring engine is the single source of truth for CareerFit calculation
    and is reused directly by the What-If simulation engine. Never duplicate this logic.

CareerFit Formula:
    CareerFit = 0.45 * SkillMatch
              + 0.20 * EvidenceStrength
              + 0.15 * ExperienceAlignment
              + 0.10 * EducationAlignment
              + 0.10 * MarketDemand

Total score is scaled and clipped to [0, 100].
Engine version: "score-1.0"
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Union

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.career_seeder import CAREER_PROFILES
from services.skill_normalizer import normalize_skill

ENGINE_VERSION = "score-1.0"

# Confidence weight mapping
CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

# Career-relevant keywords used for evaluating Experience and Projects sections
CAREER_KEYWORDS: Dict[str, List[str]] = {
    "Software Engineer": [
        "software", "engineer", "developer", "architecture", "algorithm",
        "system design", "data structures", "oop", "backend", "frontend",
        "api", "database", "git", "ci/cd", "agile", "unit test", "debugging",
        "code review", "microservices", "scalable", "production"
    ],
    "Data Scientist": [
        "data science", "machine learning", "statistical", "predictive model",
        "regression", "classification", "clustering", "hypothesis testing",
        "feature engineering", "a/b test", "exploratory data analysis", "eda",
        "pandas", "scikit-learn", "data visualization", "deep learning"
    ],
    "Machine Learning Engineer": [
        "machine learning", "deep learning", "neural network", "mlops",
        "model training", "inference", "pytorch", "tensorflow", "model serving",
        "pipeline", "docker", "gpu", "cuda", "transformer", "llm", "hugging face",
        "computer vision", "nlp", "model deployment", "model monitoring"
    ],
    "Backend Developer": [
        "backend", "server", "api", "rest", "graphql", "microservices",
        "database", "sql", "postgresql", "redis", "caching", "fastapi",
        "django", "flask", "node.js", "express", "orm", "endpoint",
        "auth", "jwt", "scalability", "load balancer"
    ],
    "Frontend Developer": [
        "frontend", "ui", "ux", "react", "vue", "angular", "javascript",
        "typescript", "html", "css", "next.js", "responsive design",
        "state management", "redux", "tailwind", "web performance",
        "accessibility", "dom", "single page application"
    ],
    "Full Stack Developer": [
        "full stack", "fullstack", "end-to-end", "client-side", "server-side",
        "frontend", "backend", "react", "node", "api", "database", "sql",
        "web application", "rest", "docker", "cloud", "ui/ux"
    ],
    "DevOps Engineer": [
        "devops", "ci/cd", "pipeline", "docker", "container", "kubernetes",
        "terraform", "infrastructure as code", "iac", "aws", "cloud", "linux",
        "bash", "automation", "monitoring", "prometheus", "grafana", "ansible",
        "jenkins", "github actions", "site reliability"
    ],
    "Data Analyst": [
        "data analyst", "analytics", "sql", "query", "excel", "power bi",
        "tableau", "dashboard", "kpi", "reporting", "business intelligence",
        "bi", "visualization", "metrics", "insights", "trend analysis"
    ],
    "Product Manager": [
        "product manager", "product management", "roadmap", "user stories",
        "backlog", "strategy", "stakeholder", "kpi", "okr", "market research",
        "user research", "mvp", "launch", "scrum", "feature prioritization",
        "analytics", "customer journey"
    ],
    "AI Engineer": [
        "artificial intelligence", "ai", "llm", "large language model",
        "prompt engineering", "langchain", "rag", "retrieval augmented generation",
        "fine-tuning", "embeddings", "vector database", "opencv", "computer vision",
        "nlp", "generative ai", "genai", "agents"
    ],
    "Cloud Engineer": [
        "cloud", "aws", "azure", "gcp", "iam", "vpc", "s3", "ec2", "lambda",
        "cloud architecture", "serverless", "kubernetes", "terraform",
        "networking", "security", "high availability", "disaster recovery"
    ],
}

# Degree keywords for Education alignment matching
TIER_1_DEGREES = [
    "computer science", "software engineering", "computer engineering",
    "data science", "machine learning", "artificial intelligence",
    "information technology", "information systems", "electrical engineering",
    "mathematics", "applied mathematics", "statistics", "physics", "computing"
]

TIER_2_DEGREES = [
    "engineering", "mechanical engineering", "civil engineering",
    "business analytics", "operations research", "management information systems",
    "quantitative", "cognitive science", "economics", "finance", "data analytics",
    "business administration", "information science"
]


def _extract_skill_names(
    skills_input: Union[Sequence[Any], Set[str], None]
) -> Set[str]:
    """Helper to extract a set of lowercase normalized skill names from any input format."""
    skill_names: Set[str] = set()
    if not skills_input:
        return skill_names

    for item in skills_input:
        name = ""
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = (
                item.get("skill_name")
                or item.get("skill")
                or item.get("name")
                or item.get("canonical_name")
                or ""
            )
        elif hasattr(item, "skill") and hasattr(item.skill, "canonical_name"):
            name = item.skill.canonical_name
        elif hasattr(item, "canonical_name"):
            name = item.canonical_name
        elif hasattr(item, "skill_name"):
            name = item.skill_name

        if name:
            clean = name.strip().lower()
            skill_names.add(clean)
            norm = normalize_skill(name).strip().lower()
            if norm:
                skill_names.add(norm)

    return skill_names


def _extract_section_text(
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None],
    target_section_keywords: Sequence[str],
) -> str:
    """Extract and aggregate text from resume sections matching specified keywords."""
    if not resume_sections:
        return ""

    if isinstance(resume_sections, str):
        return resume_sections.lower()

    collected: List[str] = []

    if isinstance(resume_sections, dict):
        for sec_name, sec_content in resume_sections.items():
            sec_lower = str(sec_name).lower()
            if any(k in sec_lower for k in target_section_keywords):
                if isinstance(sec_content, str):
                    collected.append(sec_content)
                elif isinstance(sec_content, dict):
                    collected.append(str(sec_content.get("text", "")))
                elif isinstance(sec_content, list):
                    collected.extend(str(x) for x in sec_content)

    elif isinstance(resume_sections, (list, tuple)):
        for sec in resume_sections:
            if isinstance(sec, dict):
                sec_type = str(sec.get("section_type", sec.get("name", ""))).lower()
                sec_text = str(sec.get("text", sec.get("content", "")))
            elif hasattr(sec, "section_type") and hasattr(sec, "text"):
                sec_type = str(sec.section_type).lower()
                sec_text = str(sec.text or "")
            else:
                sec_type = ""
                sec_text = str(sec)

            if any(k in sec_type for k in target_section_keywords):
                collected.append(sec_text)

    return " ".join(collected).lower()


def calculate_skill_match(
    profile_skills: Union[Sequence[Any], None],
    career_skills: Union[Sequence[Any], Dict[str, Any], None],
) -> float:
    """Calculate the match between a candidate's profile skills and career requirements.

    Args:
        profile_skills: List of dicts, models, or strings representing acquired skills.
        career_skills: List of required skills (as dicts with {skill_name, importance, required},
                       CareerSkill objects, or plain strings).

    Returns:
        Weighted match score between 0.0 and 1.0.
    """
    if not profile_skills or not career_skills:
        return 0.0

    profile_names = _extract_skill_names(profile_skills)
    if not profile_names:
        return 0.0

    # Standardize career skills into a list of tuples: (name, importance, required)
    standardized_career_skills: List[tuple[str, float, bool]] = []

    if isinstance(career_skills, dict):
        # Could be {"required_skills": [...]} from CAREER_PROFILES
        req_list = career_skills.get("required_skills", [])
        for skill_item in req_list:
            standardized_career_skills.append((str(skill_item), 1.0, True))
    else:
        for item in career_skills:
            if isinstance(item, str):
                standardized_career_skills.append((item, 1.0, True))
            elif isinstance(item, dict):
                s_name = (
                    item.get("skill_name")
                    or item.get("skill")
                    or item.get("name")
                    or item.get("canonical_name")
                    or ""
                )
                imp = float(item.get("importance", 1.0) or 1.0)
                req = bool(item.get("required", True))
                standardized_career_skills.append((s_name, imp, req))
            elif hasattr(item, "skill") and hasattr(item.skill, "canonical_name"):
                s_name = item.skill.canonical_name
                imp = float(getattr(item, "importance", 1.0) or 1.0)
                req = bool(getattr(item, "required", True))
                standardized_career_skills.append((s_name, imp, req))
            elif hasattr(item, "canonical_name"):
                standardized_career_skills.append((item.canonical_name, 1.0, True))

    if not standardized_career_skills:
        return 0.0

    total_weight = 0.0
    matched_weight = 0.0

    for s_name, importance, required in standardized_career_skills:
        weight = max(0.1, importance)
        total_weight += weight

        clean_req = s_name.strip().lower()
        norm_req = normalize_skill(s_name).strip().lower()

        if clean_req in profile_names or norm_req in profile_names:
            matched_weight += weight

    if total_weight <= 0.0:
        return 0.0

    return round(min(1.0, max(0.0, matched_weight / total_weight)), 4)


def calculate_evidence_strength(
    profile_skills: Union[Sequence[Any], None]
) -> float:
    """Calculate the average evidence strength based on skill detection confidence.

    Rules:
        - High confidence   = 1.0
        - Medium confidence = 0.6
        - Low confidence    = 0.3

    Returns:
        Weighted average float between 0.0 and 1.0.
    """
    if not profile_skills:
        return 0.0

    scores: List[float] = []

    for item in profile_skills:
        # Check if skill is verified via assessment
        is_verified = False
        if isinstance(item, dict):
            is_verified = bool(item.get("is_verified", False))
        elif hasattr(item, "is_verified"):
            is_verified = bool(getattr(item, "is_verified", False))

        if is_verified:
            scores.append(1.0)
            continue

        conf_val = None
        if isinstance(item, dict):
            conf_val = item.get("confidence")
        elif hasattr(item, "confidence"):
            conf_val = getattr(item, "confidence")

        if conf_val is None:
            # Default to medium if unspecified
            scores.append(0.6)
        elif isinstance(conf_val, str):
            key = conf_val.strip().lower()
            scores.append(CONFIDENCE_WEIGHTS.get(key, 0.6))
        elif isinstance(conf_val, (int, float)):
            # Direct numeric rating (0.0 - 1.0)
            if conf_val >= 0.75:
                scores.append(1.0)
            elif conf_val >= 0.45:
                scores.append(0.6)
            else:
                scores.append(0.3)
        else:
            scores.append(0.6)

    if not scores:
        return 0.0

    avg_evidence = sum(scores) / len(scores)
    return round(min(1.0, max(0.0, avg_evidence)), 4)


def calculate_experience_alignment(
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None],
    career_name: str,
) -> float:
    """Check if Projects and Experience sections mention career-relevant keywords.

    Returns:
        Float between 0.0 and 1.0.
    """
    if not resume_sections:
        return 0.0

    # Extract text from experience and project sections
    exp_text = _extract_section_text(
        resume_sections,
        target_section_keywords=["experience", "project", "work", "employment", "history"],
    )

    if not exp_text:
        # Fall back to checking whole document if sections were not explicitly segmented
        if isinstance(resume_sections, str):
            exp_text = resume_sections.lower()
        else:
            return 0.0

    # Get keywords for this career role
    keywords = CAREER_KEYWORDS.get(career_name, [])
    if not keywords:
        # Generic engineering keywords if role is custom
        keywords = CAREER_KEYWORDS["Software Engineer"]

    matched_count = 0
    for kw in keywords:
        pattern = rf"(?<!\w){re.escape(kw.lower())}(?!\w)"
        if re.search(pattern, exp_text):
            matched_count += 1

    # 5 or more distinct keyword mentions yields a full score of 1.0
    benchmark = 5.0
    score = matched_count / benchmark
    return round(min(1.0, max(0.0, score)), 4)


def calculate_education_alignment(
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None],
    career_name: str,
) -> float:
    """Evaluate candidate's degree and field of study against career role.

    Rules:
        - CS / Engineering / Math / Exact match -> 1.0
        - Related technical / quantitative fields -> 0.6
        - Other degrees / education listed      -> 0.3
        - No education found                    -> 0.0

    Returns:
        Float between 0.0 and 1.0.
    """
    if not resume_sections:
        return 0.0

    edu_text = _extract_section_text(
        resume_sections,
        target_section_keywords=["education", "academic", "university", "college", "degree"],
    )

    if not edu_text:
        # If no explicit education section, look for degrees in text if string passed
        if isinstance(resume_sections, str):
            edu_text = resume_sections.lower()
        else:
            return 0.0

    if not edu_text.strip():
        return 0.0

    # 1. Tier 1 Check: CS / Engineering / Math (1.0)
    for kw in TIER_1_DEGREES:
        pattern = rf"(?<!\w){re.escape(kw)}(?!\w)"
        if re.search(pattern, edu_text):
            return 1.0

    # Special handling: Product Manager & Data Analyst also match Business / Economics at 1.0
    if career_name in ("Product Manager", "Data Analyst"):
        if re.search(r"\b(business\s+administration|mba|economics|finance)\b", edu_text):
            return 1.0

    # 2. Tier 2 Check: Related fields (0.6)
    for kw in TIER_2_DEGREES:
        pattern = rf"(?<!\w){re.escape(kw)}(?!\w)"
        if re.search(pattern, edu_text):
            return 0.6

    # 3. Tier 3 Check: Any other recognized degree / education listed (0.3)
    general_edu_markers = [
        "bachelor", "master", "phd", "b.s", "b.a", "m.s", "btech", "mtech",
        "degree", "diploma", "university", "college", "institute", "school"
    ]
    if any(re.search(rf"\b{re.escape(m)}\b", edu_text) for m in general_edu_markers):
        return 0.3

    return 0.0


def calculate_career_fit(
    profile_skills: Union[Sequence[Any], None],
    career: Union[str, Dict[str, Any], Any],
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None],
    market_demand: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate the comprehensive CareerFit score for a specific career role.

    Formula:
        CareerFit = 0.45 * SkillMatch
                  + 0.20 * EvidenceStrength
                  + 0.15 * ExperienceAlignment
                  + 0.10 * EducationAlignment
                  + 0.10 * MarketDemand

    Returns a dict with:
        total_score (clipped 0-100)
        components: {skill_match, evidence_strength, experience_alignment,
                     education_alignment, market_demand}
        engine_version: "score-1.0"
    """
    # Resolve career name and required skills
    career_name: str = ""
    career_skills: List[Any] = []

    if isinstance(career, str):
        career_name = career
        if career in CAREER_PROFILES:
            career_skills = CAREER_PROFILES[career]["required_skills"]  # type: ignore
    elif isinstance(career, dict):
        career_name = career.get("name") or career.get("role") or ""
        career_skills = (
            career.get("required_skills")
            or career.get("career_skills")
            or (CAREER_PROFILES.get(career_name, {}).get("required_skills", []))
        )
    elif hasattr(career, "name"):
        career_name = career.name
        if hasattr(career, "career_skills"):
            career_skills = career.career_skills
        elif career_name in CAREER_PROFILES:
            career_skills = CAREER_PROFILES[career_name]["required_skills"]  # type: ignore

    # Calculate individual components
    skill_match = calculate_skill_match(profile_skills, career_skills)
    evidence_strength = calculate_evidence_strength(profile_skills)
    experience_alignment = calculate_experience_alignment(resume_sections, career_name)
    education_alignment = calculate_education_alignment(resume_sections, career_name)

    # Market demand (default to 0.5 if not provided)
    if market_demand is None:
        market_demand = 0.5
    demand_val = round(min(1.0, max(0.0, float(market_demand))), 4)

    # Compute weighted total
    raw_fit = (
        0.45 * skill_match
        + 0.20 * evidence_strength
        + 0.15 * experience_alignment
        + 0.10 * education_alignment
        + 0.10 * demand_val
    )

    total_score = round(min(100.0, max(0.0, raw_fit * 100.0)), 2)

    return {
        "career_name": career_name,
        "total_score": total_score,
        "components": {
            "skill_match": skill_match,
            "evidence_strength": evidence_strength,
            "experience_alignment": experience_alignment,
            "education_alignment": education_alignment,
            "market_demand": demand_val,
        },
        "engine_version": ENGINE_VERSION,
    }


def rank_careers(
    profile_skills: Union[Sequence[Any], None],
    resume_sections: Union[Dict[str, Any], Sequence[Any], str, None],
    all_careers: Optional[Sequence[Any]] = None,
    demand_scores: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Rank all careers for a given candidate profile by CareerFit score in descending order.

    Args:
        profile_skills: List of candidate skills with confidence.
        resume_sections: Candidate resume sections.
        all_careers: Optional list of career names, dicts, or CareerRole objects.
                     Defaults to the 10 canonical roles from CAREER_PROFILES.
        demand_scores: Optional dict mapping career names to demand scores.
                       Attempts to load data/processed/demand_scores.json if None.

    Returns:
        Sorted list of career fit results (highest total_score first).
    """
    if all_careers is None:
        all_careers = list(CAREER_PROFILES.keys())

    # Try loading demand_scores from processed JSON if not provided
    if demand_scores is None:
        scores_file = PROJECT_ROOT / "data" / "processed" / "demand_scores.json"
        if scores_file.exists():
            try:
                with open(scores_file, "r", encoding="utf-8") as f:
                    demand_scores = json.load(f)
            except Exception:
                demand_scores = {}
        else:
            demand_scores = {}

    results: List[Dict[str, Any]] = []

    for career in all_careers:
        c_name = career if isinstance(career, str) else getattr(career, "name", str(career))
        if isinstance(career, dict):
            c_name = career.get("name", c_name)

        market_demand = demand_scores.get(c_name, 0.5) if demand_scores else 0.5
        fit_result = calculate_career_fit(
            profile_skills=profile_skills,
            career=career,
            resume_sections=resume_sections,
            market_demand=market_demand,
        )
        results.append(fit_result)

    # Sort descending by total_score
    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results

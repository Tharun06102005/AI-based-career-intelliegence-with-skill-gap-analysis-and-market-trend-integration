"""ATS (Applicant Tracking System) Scorer service.

Extracts keywords and skills from the job description and compares them against
the candidate's resume to calculate ATS alignment, keyword coverage, and
actionable optimization recommendations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set
from services.skill_extractor import extract_skills_from_text
from services.skill_normalizer import normalize_all_skills


def _extract_unique_skills(text: str, section_name: str = "content") -> Set[str]:
    """Extract canonical skills from text using existing regex & normalizer pipeline."""
    if not text:
        return set()
    raw_skills = extract_skills_from_text(text, section_name)
    normalized = normalize_all_skills(raw_skills)
    return {item["skill_name"] for item in normalized if item.get("skill_name")}


def calculate_ats_score(resume_text: str, job_description: str) -> Dict[str, Any]:
    """Calculate ATS compatibility score and gap analysis.

    Parameters:
        resume_text: Raw plain text of the resume sections.
        job_description: Target job description pasted by user.

    Returns:
        Dict with ats_score, match_percentage, matched_keywords,
        missing_keywords, and recommendations.
    """
    if not job_description or not job_description.strip():
        return {
            "ats_score": 0,
            "match_percentage": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendations": ["Please provide a valid job description to evaluate."],
        }

    # Extract skills from JD and Resume
    jd_skills_set = _extract_unique_skills(job_description, "job_description")
    resume_skills_set = _extract_unique_skills(resume_text, "resume")

    # If few canonical skills matched from JD, scan for common high-impact keywords
    common_tech_terms = [
        "API", "REST", "CI/CD", "Cloud", "Microservices", "Security",
        "Architecture", "Scalability", "Testing", "Agile", "DevOps",
        "Distributed Systems", "Database", "Frontend", "Backend", "Full Stack"
    ]
    for term in common_tech_terms:
        if re.search(rf"\b{re.escape(term)}\b", job_description, re.IGNORECASE):
            jd_skills_set.add(term)
        if re.search(rf"\b{re.escape(term)}\b", resume_text, re.IGNORECASE):
            resume_skills_set.add(term)

    # Keyword matching: check direct membership or regex presence in resume_text
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []

    for skill in sorted(jd_skills_set):
        # Match either via normalized skill set or direct textual appearance in resume
        pattern = rf"(?<!\w){re.escape(skill)}(?!\w)"
        if skill in resume_skills_set or re.search(pattern, resume_text, re.IGNORECASE):
            matched_keywords.append(skill)
        else:
            missing_keywords.append(skill)

    total_jd = len(jd_skills_set)
    if total_jd > 0:
        keyword_match_pct = round((len(matched_keywords) / total_jd) * 100)
    else:
        keyword_match_pct = 70

    # ATS Formatting & Content factors
    resume_lower = resume_text.lower()
    
    # Check for standard sections
    section_bonus = 0
    sections = ["experience", "education", "skill", "project"]
    for s in sections:
        if s in resume_lower:
            section_bonus += 2.5  # up to 10 points

    # Check for quantifiable impact (numbers, percentages, metrics)
    metrics_matches = len(re.findall(r"\b\d+([%kKmM+]|\s*(?:percent|years|users|revenue))\b", resume_text))
    metric_bonus = min(15, metrics_matches * 3)

    # Action verbs check
    action_verbs = ["developed", "built", "engineered", "implemented", "optimized", "managed", "led", "architected", "deployed", "scaled"]
    verbs_found = sum(1 for v in action_verbs if v in resume_lower)
    verb_bonus = min(10, verbs_found * 2)

    # Weighted ATS score: 65% keyword match + 35% formatting/metrics/verbs
    raw_ats_score = (keyword_match_pct * 0.65) + section_bonus + metric_bonus + verb_bonus
    ats_score = int(max(10, min(98, round(raw_ats_score))))

    # Formulate recommendations
    recommendations: List[str] = []
    if missing_keywords:
        top_missing = missing_keywords[:6]
        recommendations.append(
            f"Incorporate missing core keywords from the job description: {', '.join(top_missing)}."
        )

    if metric_bonus < 9:
        recommendations.append(
            "Add measurable metrics and numbers (e.g., 'improved performance by 30%', 'scaled to 10,000+ users') to validate your achievements."
        )

    if verb_bonus < 6:
        recommendations.append(
            "Begin bullet points with strong technical action verbs such as 'Architected', 'Optimized', 'Engineered', and 'Implemented'."
        )

    if ats_score < 75:
        recommendations.append(
            "Mirror the exact phrasing and titles from the job description in your summary and experience sections."
        )
    else:
        recommendations.append(
            "High keyword match found! Your resume passes primary ATS parsing filters."
        )

    recommendations.append(
        "Maintain a single-column clean format without complex graphics or tables to prevent parsing anomalies."
    )

    return {
        "ats_score": ats_score,
        "match_percentage": keyword_match_pct,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "recommendations": recommendations,
    }

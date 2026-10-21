"""LLM Explanation and Roadmap Generation Service.

CRITICAL RULE:
    The LLM ONLY explains computed results.
    It NEVER calculates, overrides, or alters any scores.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from groq import Groq

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.config import settings
from services.skill_normalizer import normalize_skill

# Primary model requested; fallback models if deprecated on Groq cloud
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "llama3-8b-8192"]

EXPLANATION_PROMPT = """You are an expert AI Career Intelligence Advisor.
Explain the candidate's computed CareerFit and Readiness scores clearly and concisely.

CRITICAL RULES:
- You are ONLY explaining already-computed facts and numerical scores.
- NEVER recalculate, override, or change any scores.
- Return ONLY a valid JSON object matching the schema below. No markdown text outside the JSON.

FACTS ABOUT CANDIDATE & ROLE:
- Target Career Role: {career_name}
- Computed CareerFit Score: {fit_score} / 100
- Computed Readiness Score: {readiness} / 100
- Market Demand Score: {market_demand}
- Matched Skills: {matched_skills}
- Missing Skills: {missing_skills}
{simulation_info}

JSON SCHEMA:
{{
  "summary": "2-3 sentence explanation summarizing how well the profile aligns with the role and what is needed next.",
  "strengths": ["Clear strength 1 based on matched skills", "Clear strength 2"],
  "gaps": [
    {{"skill": "SkillName", "reason": "Why this missing skill is critical for this role"}}
  ],
  "roadmap": [
    {{
      "skill": "SkillName",
      "steps": ["Step 1", "Step 2", "Step 3"]
    }}
  ],
  "caveats": ["Important caveat or realistic market context"]
}}
"""

ROADMAP_PROMPT = """You are a technical mentor designing a targeted day-by-day learning roadmap for missing skills.

Career Role: {career_name}
Total Available Study Days: {days_available} days
Skills Breakdown:
{skills_breakdown}

For each missing skill, provide a structured plan with:
- "skill": Canonical name of the skill
- "days_allocated": e.g. "Day 1-5"
- "daily_tasks": An array of sequential daily tasks (each string formatted as "Day X: Specific actionable task")
- "youtube_link": YouTube tutorial URL (e.g. https://youtube.com/watch?v=...)
- "resources": 2 high-quality recommended resources (e.g. Official Documentation, Coursera course)

Return ONLY valid JSON matching this schema:
[
  {{
    "skill": "SkillName",
    "days_allocated": "Day 1-5",
    "daily_tasks": [
      "Day 1: Understand core concepts and installation",
      "Day 2: Build a basic starter module",
      "Day 3: Implement intermediate feature",
      "Day 4: Integrate with database/API",
      "Day 5: Deploy real project and optimize"
    ],
    "youtube_link": "https://youtube.com/...",
    "resources": ["Official Documentation", "FreeCodeCamp / Coursera"]
  }}
]
"""

# Curated fallback knowledge base for learning steps & resources
CURATED_SKILL_RESOURCES: Dict[str, Dict[str, Any]] = {
    "Docker": {
        "steps": [
            "Learn containerization basics, Dockerfile syntax, and images",
            "Build multi-stage images and manage volumes and networks",
            "Orchestrate multi-container applications with Docker Compose",
        ],
        "resources": ["Docker Official Documentation", "Play with Docker Labs"],
    },
    "Kubernetes": {
        "steps": [
            "Understand Pods, Deployments, and Services architecture",
            "Configure ConfigMaps, Secrets, and Ingress controllers",
            "Deploy and scale sample microservices on a local Minikube cluster",
        ],
        "resources": ["Kubernetes.io Tutorials", "KubeAcademy by VMware"],
    },
    "REST APIs": {
        "steps": [
            "Master HTTP methods, status codes, headers, and REST constraints",
            "Implement secure authentication with JWT and rate limiting",
            "Document and test endpoints using OpenAPI/Swagger and Postman",
        ],
        "resources": ["RESTful API Design Best Practices", "Postman Learning Center"],
    },
    "SQL": {
        "steps": [
            "Master complex SELECT queries, JOINs, aggregations, and subqueries",
            "Learn database normalization, indexing, and query execution plans",
            "Write transactional statements and database schema migrations",
        ],
        "resources": ["PostgreSQL Official Tutorial", "Mode Analytics SQL Tutorial"],
    },
    "Java": {
        "steps": [
            "Review core Java syntax, OOP principles, and Collections Framework",
            "Learn concurrency, streams, and functional programming features",
            "Build RESTful services using Spring Boot and Hibernate ORM",
        ],
        "resources": ["Oracle Java Documentation", "Baeldung Spring Boot Tutorials"],
    },
    "Python": {
        "steps": [
            "Master idiomatic Python, data structures, and type hinting",
            "Build asynchronous web APIs using FastAPI and Pydantic",
            "Write comprehensive unit and integration tests using pytest",
        ],
        "resources": ["Real Python Guides", "FastAPI Official Documentation"],
    },
    "AWS": {
        "steps": [
            "Understand foundational services: IAM, EC2, S3, and VPC",
            "Implement serverless applications with AWS Lambda and API Gateway",
            "Deploy reproducible cloud infrastructure using AWS CDK or Terraform",
        ],
        "resources": ["AWS Skill Builder", "AWS Documentation & Architecture Center"],
    },
    "Git": {
        "steps": [
            "Master branching, merging, rebasing, and resolving conflicts",
            "Implement Git workflows: feature branching and trunk-based development",
            "Automate testing and deployments with GitHub Actions CI/CD",
        ],
        "resources": ["Pro Git Book", "GitHub Skills Interactive Labs"],
    },
}


def call_groq_llm(prompt: str, model: str = PRIMARY_MODEL) -> str:
    """Call Groq API with prompt using llama3-8b-8192 (or active fallback).

    Max tokens: 1500. Returns raw response text.
    """
    if not settings.groq_api_key:
        print("[Warning] GROQ_API_KEY is not configured in environment.")
        return ""

    client = Groq(api_key=settings.groq_api_key)
    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]

    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an objective AI career intelligence assistant. "
                            "You only output valid, parseable JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=m,
                max_tokens=1500,
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            if content.strip():
                return content
        except Exception as e:
            # If model is deprecated or inaccessible, attempt fallback model
            print(f"[LLM] Model '{m}' call failed: {e}. Trying fallback if available.")
            continue

    return ""


def parse_llm_response(
    response_text: str,
    matched_skills: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Extract and validate JSON from Groq LLM response.

    If invalid JSON or parsing error, returns the deterministic fallback:
        {
            "summary": "Based on your profile analysis...",
            "strengths": matched_skills[:3],
            "gaps": missing_skills[:3],
            "roadmap": [],
            "caveats": ["AI explanation unavailable"]
        }
    """
    matched = matched_skills or []
    missing = missing_skills or []

    fallback: Dict[str, Any] = {
        "summary": (
            "Based on your profile analysis, you possess valuable core strengths "
            "for this career role, but addressing your primary missing technical skills "
            "will significantly improve your market readiness."
        ),
        "strengths": matched[:3],
        "gaps": missing[:3],
        "roadmap": [],
        "caveats": ["AI explanation unavailable"],
    }

    if not response_text or not response_text.strip():
        return fallback

    # Extract JSON substring (handles markdown fences or surrounding chatter)
    text = response_text.strip()
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if json_match:
        text = json_match.group(1).strip()
    else:
        # Match from first '{' to last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return fallback

        # Validate essential keys and types
        summary = str(data.get("summary") or fallback["summary"])
        strengths = (
            data.get("strengths")
            if isinstance(data.get("strengths"), list)
            else matched[:3]
        )
        gaps = (
            data.get("gaps")
            if isinstance(data.get("gaps"), list)
            else missing[:3]
        )
        roadmap = (
            data.get("roadmap")
            if isinstance(data.get("roadmap"), list)
            else []
        )
        caveats = (
            data.get("caveats")
            if isinstance(data.get("caveats"), list)
            else ["AI explanation unavailable"]
        )

        return {
            "summary": summary,
            "strengths": strengths,
            "gaps": gaps,
            "roadmap": roadmap,
            "caveats": caveats,
        }
    except Exception:
        return fallback


def generate_explanation(
    career_fit_result: Dict[str, Any],
    gap_report: Dict[str, Any],
    simulation_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a structured, natural language explanation of computed scores.

    CRITICAL RULE:
        The LLM only explains computed results. It NEVER calculates or overrides scores.
    """
    career_name = (
        career_fit_result.get("career_name")
        or gap_report.get("career_name")
        or "Target Role"
    )
    fit_score = career_fit_result.get("total_score", 0.0)
    readiness = gap_report.get("readiness", 0.0)
    matched_skills = gap_report.get("matched_skills", [])
    missing_skills = gap_report.get("missing_skills", [])
    market_demand = career_fit_result.get("components", {}).get(
        "market_demand", 0.5
    )

    simulation_info = ""
    if simulation_result and "delta" in simulation_result:
        delta = simulation_result["delta"]
        simulation_info = (
            f"- What-If Simulation Applied: Added {simulation_result.get('added_skills', [])}, "
            f"Removed {simulation_result.get('removed_skills', [])}\n"
            f"- Projected Score Delta: CareerFit {delta.get('career_fit_score', 0):+0.2f}, "
            f"Readiness {delta.get('readiness', 0):+0.2f}%, "
            f"Missing Skills {delta.get('missing_skills_count', 0):+d}"
        )

    # Format structured prompt
    prompt = EXPLANATION_PROMPT.format(
        career_name=career_name,
        fit_score=fit_score,
        readiness=readiness,
        market_demand=market_demand,
        matched_skills=", ".join(matched_skills) if matched_skills else "None",
        missing_skills=", ".join(missing_skills) if missing_skills else "None",
        simulation_info=simulation_info,
    )

    # Call LLM and parse response
    raw_response = call_groq_llm(prompt)
    explanation = parse_llm_response(
        raw_response,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )

    # Enforce non-overridable computed scores in returned envelope
    return {
        "career_name": career_name,
        "fit_score": fit_score,
        "readiness": readiness,
        "explanation": explanation,
    }


SKILL_YOUTUBE_LINKS: Dict[str, str] = {
    "python": "https://youtube.com/watch?v=_uQrJ0TkZlc",
    "javascript": "https://youtube.com/watch?v=W6NZfCO5SIk",
    "react": "https://youtube.com/watch?v=bMknfKXIFA8",
    "docker": "https://youtube.com/watch?v=3c-iBn73dDE",
    "sql": "https://youtube.com/watch?v=HXV3zeQKqGY",
    "machine learning": "https://youtube.com/watch?v=NWONeJKn9Kc",
    "aws": "https://youtube.com/watch?v=3hLmDS179YE",
    "git": "https://youtube.com/watch?v=RGOj5yH7evk",
    "typescript": "https://youtube.com/watch?v=30LWjhZzg50",
    "node.js": "https://youtube.com/watch?v=Oe421EPjeBE",
    "nodejs": "https://youtube.com/watch?v=Oe421EPjeBE",
    "kubernetes": "https://youtube.com/watch?v=X48VuDVv0do",
    "tensorflow": "https://youtube.com/watch?v=tPYj3fFJGjk",
    "rest apis": "https://youtube.com/watch?v=GZvSYJDk-us",
    "rest": "https://youtube.com/watch?v=GZvSYJDk-us",
    "api": "https://youtube.com/watch?v=GZvSYJDk-us",
    "golang": "https://youtube.com/watch?v=un6ZyFkqFKo",
    "go": "https://youtube.com/watch?v=un6ZyFkqFKo",
    "java": "https://youtube.com/watch?v=eIrMbAQSU34",
    "c++": "https://youtube.com/watch?v=vLnPwxZdW4Y",
    "cpp": "https://youtube.com/watch?v=vLnPwxZdW4Y",
    "linux": "https://youtube.com/watch?v=wBp0Rb-ZJak",
    "graphql": "https://youtube.com/watch?v=eIQh02xuVw4",
    "postgresql": "https://youtube.com/watch?v=qw--VYLpxG4",
    "postgres": "https://youtube.com/watch?v=qw--VYLpxG4",
    "redis": "https://youtube.com/watch?v=jgpVdJB2sKQ",
    "system design": "https://youtube.com/watch?v=m8Icp_Cid5o",
    "ci/cd": "https://youtube.com/watch?v=scEDHsr3APg",
    "cicd": "https://youtube.com/watch?v=scEDHsr3APg",
    "next.js": "https://youtube.com/watch?v=843nec-IvW0",
    "nextjs": "https://youtube.com/watch?v=843nec-IvW0",
}


def get_youtube_link(skill_name: str) -> str:
    norm = skill_name.lower().strip()
    if norm in SKILL_YOUTUBE_LINKS:
        return SKILL_YOUTUBE_LINKS[norm]
    for k, v in SKILL_YOUTUBE_LINKS.items():
        if k in norm or norm in k:
            return v
    return f"https://youtube.com/results?search_query={skill_name.replace(' ', '+')}+tutorial"


def generate_roadmap(
    missing_skills: Sequence[str],
    career_name: str = "Software Engineer",
    days_available: int = 30,
) -> List[Dict[str, Any]]:
    """Generate sequential learning steps and day-by-day schedule for missing technical skills."""
    if not missing_skills:
        return []

    clean_skills = [str(s).strip() for s in missing_skills if str(s).strip()]
    if not clean_skills:
        return []

    total_skills = len(clean_skills)
    days_available = max(total_skills * 2, int(days_available or 30))
    days_per_skill = max(2, days_available // total_skills)

    # Pre-calculate allocated days per skill
    allocations = []
    current_day = 1
    for i, s in enumerate(clean_skills):
        start_d = current_day
        if i == total_skills - 1:
            end_d = days_available
        else:
            end_d = min(days_available, current_day + days_per_skill - 1)
        current_day = end_d + 1
        day_label = f"Day {start_d}-{end_d}" if start_d != end_d else f"Day {start_d}"
        allocations.append({
            "skill": s,
            "start_day": start_d,
            "end_day": end_d,
            "day_label": day_label,
            "days_count": max(1, end_d - start_d + 1),
        })

    skills_breakdown = "\n".join(
        f"- {a['skill']}: {a['day_label']} ({a['days_count']} days)"
        for a in allocations
    )

    prompt = ROADMAP_PROMPT.format(
        career_name=career_name,
        days_available=days_available,
        skills_breakdown=skills_breakdown,
    )
    raw_response = call_groq_llm(prompt)

    roadmap_items: List[Dict[str, Any]] = []

    if raw_response:
        text = raw_response.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if json_match:
            text = json_match.group(1).strip()
        else:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "skill" in item:
                        skill_name = str(item.get("skill"))
                        alloc = next(
                            (a for a in allocations if a["skill"].lower() == skill_name.lower()),
                            None,
                        )
                        days_label = str(item.get("days_allocated") or (alloc["day_label"] if alloc else f"Day 1-{days_per_skill}"))
                        daily_tasks = list(item.get("daily_tasks") or item.get("steps") or [])
                        youtube_link = str(item.get("youtube_link") or get_youtube_link(skill_name))
                        resources = list(item.get("resources") or [])

                        roadmap_items.append({
                            "skill": skill_name,
                            "days_allocated": days_label,
                            "daily_tasks": daily_tasks,
                            "steps": daily_tasks,
                            "youtube_link": youtube_link,
                            "resources": resources,
                        })
        except Exception:
            pass

    # Ensure all missing skills have complete structured entries
    generated_skills = {item["skill"].lower() for item in roadmap_items}
    for alloc in allocations:
        s = alloc["skill"]
        if s.lower() not in generated_skills:
            canonical = normalize_skill(s)
            yt_link = get_youtube_link(s)
            start_d = alloc["start_day"]
            end_d = alloc["end_day"]

            default_milestones = [
                f"Understand {s} core principles, architecture, and setup",
                f"Write fundamental syntax and practice core patterns with {s}",
                f"Implement practical real-world modules and component integration in {s}",
                f"Connect {s} with databases, REST APIs, and external services",
                f"Complete hands-on project and learn production deployment best practices for {s}",
            ]

            daily_tasks = []
            for d_idx, day_num in enumerate(range(start_d, end_d + 1)):
                task_desc = default_milestones[min(d_idx, len(default_milestones) - 1)]
                daily_tasks.append(f"Day {day_num}: {task_desc}")

            curated = CURATED_SKILL_RESOURCES.get(canonical) or CURATED_SKILL_RESOURCES.get(s)
            resources = list(curated["resources"]) if curated else [
                f"{s} Official Documentation",
                f"FreeCodeCamp: {s} Full Course",
            ]

            roadmap_items.append({
                "skill": s,
                "days_allocated": alloc["day_label"],
                "daily_tasks": daily_tasks,
                "steps": daily_tasks,
                "youtube_link": yt_link,
                "resources": resources,
            })

    # Sort roadmap items to match allocations order
    alloc_order = {a["skill"].lower(): idx for idx, a in enumerate(allocations)}
    roadmap_items.sort(key=lambda item: alloc_order.get(item["skill"].lower(), 999))

    return roadmap_items

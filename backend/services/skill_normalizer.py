"""Normalize extracted skill names to canonical forms and deduplicate.

Lookup order in :func:`normalize_skill`:

1. lowercase / trim / unicode-normalize the raw string
2. exact alias lookup in ``SKILL_ALIASES``
3. exact canonical-name lookup (``SKILL_PATTERNS`` + alias targets)
4. fuzzy match via :mod:`difflib` (cutoff 0.82)
5. pass through the trimmed original unchanged
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Union

from services.skill_extractor import SKILL_PATTERNS

# Short forms / alternate spellings -> canonical skill name (50+ mappings).
SKILL_ALIASES: Dict[str, str] = {
    # --- core abbreviations ---
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "postgres": "PostgreSQL",
    "mongo": "MongoDB",
    "k8s": "Kubernetes",
    "tf": "TensorFlow",
    "sklearn": "Scikit-learn",
    "node": "Node.js",
    "vue": "Vue.js",
    "next": "Next.js",
    "rest": "REST APIs",
    "dl": "Deep Learning",
    "cv": "Computer Vision",
    "nlp": "Natural Language Processing",
    "react native": "React Native",
    "gcp": "Google Cloud",
    "aws": "Amazon Web Services",
    "gh": "GitHub",
    "vscode": "VS Code",
    "dsa": "Data Structures",
    "oop": "Object Oriented Programming",
    "db": "Database",
    "api": "REST APIs",
    "cicd": "CI/CD",
    "mlops": "MLOps",
    "genai": "Generative AI",
    "llm": "Large Language Models",
    # --- spelling variants / common short forms ---
    "nodejs": "Node.js",
    "node js": "Node.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "nextjs": "Next.js",
    "next js": "Next.js",
    "angularjs": "Angular",
    "spring": "Spring Boot",
    "springboot": "Spring Boot",
    "spring framework": "Spring Boot",
    "rest api": "REST APIs",
    "restful": "REST APIs",
    "restful apis": "REST APIs",
    "fast api": "FastAPI",
    "scikit learn": "Scikit-learn",
    "torch": "PyTorch",
    "np": "NumPy",
    "pd": "Pandas",
    "powerbi": "Power BI",
    "tailwind css": "Tailwind",
    "tailwindcss": "Tailwind",
    "html5": "HTML",
    "css3": "CSS",
    "mongo db": "MongoDB",
    "gcloud": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "ci cd": "CI/CD",
    "ci-cd": "CI/CD",
    "continuous integration": "CI/CD",
    "gen ai": "Generative AI",
    "llms": "Large Language Models",
    "large language model": "Large Language Models",
    "data structures and algorithms": "Data Structures",
    "oops": "Object Oriented Programming",
    "dbms": "Database",
    "oauth2": "OAuth",
    "jwt token": "JWT",
    "json web token": "JWT",
    "golang": "Go",
    "cpp": "C++",
    "csharp": "C#",
    "c sharp": "C#",
    "python3": "Python",
    "java script": "JavaScript",
}

# Canonical vocabulary: extractor patterns + every alias target.
_CANONICAL_BY_LOWER: Dict[str, str] = {
    name.lower(): name for name in sorted(set(SKILL_PATTERNS) | set(SKILL_ALIASES.values()))
}
_CANONICAL_KEYS: List[str] = list(_CANONICAL_BY_LOWER)

_FUZZY_CUTOFF = 0.82

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def normalize_skill(raw_skill: Union[str, None]) -> str:
    """Map a raw skill string to its canonical name.

    lowercase -> trim -> alias dict -> exact canonical -> fuzzy -> as-is.
    """
    original = "" if raw_skill is None else str(raw_skill).strip()
    if not original:
        return ""

    key = unicodedata.normalize("NFKC", original).lower().strip()
    key = re.sub(r"\s+", " ", key).strip(" .:;,-")

    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]
    if key in _CANONICAL_BY_LOWER:
        return _CANONICAL_BY_LOWER[key]

    matches = difflib.get_close_matches(key, _CANONICAL_KEYS, n=1, cutoff=_FUZZY_CUTOFF)
    if matches:
        return _CANONICAL_BY_LOWER[matches[0]]
    return original


def _rank(confidence: Union[str, float, int, None]) -> int:
    """Ordering key for confidences given as labels ("High") or scores (0.9)."""
    if isinstance(confidence, str):
        return _CONFIDENCE_RANK.get(confidence.strip().lower(), 0)
    if isinstance(confidence, (int, float)):
        if confidence >= 0.75:
            return 3
        if confidence >= 0.45:
            return 2
        return 1 if confidence > 0 else 0
    return 0


def _skill_name_of(entry: dict) -> str:
    return (
        entry.get("skill_name")
        or entry.get("skill")
        or entry.get("name")
        or entry.get("raw_text")
        or ""
    )


def normalize_all_skills(
    skills_list: Union[List[dict], List[str], None],
) -> List[dict]:
    """Normalize every skill and deduplicate, keeping the highest confidence.

    Accepts the dicts produced by ``extract_all_skills`` (keys like
    ``skill_name``/``confidence``/``section``) or plain strings. The first
    occurrence's position is preserved; a later duplicate only replaces it
    when its confidence ranks higher.
    """
    if not skills_list:
        return []

    best: Dict[str, dict] = {}
    order: List[str] = []

    for entry in skills_list:
        if isinstance(entry, dict):
            item = dict(entry)
            raw = _skill_name_of(entry)
        else:
            raw = str(entry)
            item = {"raw_text": raw}

        canonical = normalize_skill(raw)
        if not canonical:
            continue
        item["skill_name"] = canonical

        existing = best.get(canonical)
        if existing is None:
            best[canonical] = item
            order.append(canonical)
        elif _rank(item.get("confidence")) > _rank(existing.get("confidence")):
            best[canonical] = item

    return [best[name] for name in order]

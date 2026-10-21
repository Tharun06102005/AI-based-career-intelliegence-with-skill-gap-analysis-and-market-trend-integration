"""Skill extraction from parsed resume sections: regex matching + confidence.

``SKILL_PATTERNS`` holds canonical skill names; matching compiles them into two
case-insensitive/case-sensitive regexes (longest name first, so "JavaScript"
wins over "Java" and "C++" over "C"). Alternate spellings listed in
``_SKILL_VARIANTS`` resolve to the same canonical name.
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

# Canonical names of common tech skills matched against resume text (100+).
SKILL_PATTERNS: List[str] = [
    # Programming languages
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust",
    "C", "C++", "C#", "Kotlin", "Swift", "Ruby", "PHP", "Scala",
    "R", "MATLAB", "Dart", "Bash", "SQL",
    # Frontend
    "React", "Vue.js", "Angular", "Svelte", "Next.js",
    "HTML", "CSS", "Sass", "Tailwind", "Bootstrap", "Redux",
    # Backend & APIs
    "Node.js", "Express.js", "FastAPI", "Flask", "Django",
    "Spring Boot", "GraphQL", "gRPC", "REST APIs", "Prisma",
    # Data stores & messaging
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "SQLite", "Snowflake", "Kafka", "RabbitMQ",
    # Machine learning & data science
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "Pandas",
    "NumPy", "Matplotlib", "Seaborn", "OpenCV", "Hugging Face",
    "LLM", "LangChain", "Data Analysis",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
    "Ansible", "Jenkins", "GitHub Actions", "CI/CD", "Linux",
    "Git", "Prometheus", "Grafana", "Nginx",
    # Big data & analytics
    "Spark", "Hadoop", "Airflow", "dbt", "Power BI", "Tableau", "Excel",
    # Mobile & backend-as-a-service
    "React Native", "Flutter", "Firebase", "Supabase",
    # Practices & tooling
    "Agile", "Scrum", "Jira", "OAuth", "JWT", "pytest", "Selenium",
    "Unit Testing", "Microservices", "Hibernate",
]

# Alternate spellings/short forms -> canonical skill (matched case-insensitively).
_SKILL_VARIANTS: Dict[str, List[str]] = {
    "React": ["React.js", "ReactJS"],
    "Vue.js": ["Vue", "VueJS"],
    "Next.js": ["NextJS", "Next JS"],
    "Node.js": ["NodeJS", "Node JS"],
    "Express.js": ["ExpressJS"],
    "Spring Boot": ["Spring", "Spring Framework", "Spring MVC"],
    "REST APIs": ["REST API", "RESTful API", "RESTful APIs"],
    "Scikit-learn": ["sklearn", "scikit learn"],
    "PostgreSQL": ["Postgres"],
    "MongoDB": ["Mongo"],
    "Kubernetes": ["K8s"],
    "Go": ["Golang"],
    "JavaScript": ["JS"],
    "TypeScript": ["TS"],
    "Tailwind": ["Tailwind CSS"],
}

# Matched case-sensitively: lowercase forms are ordinary English words
# ("go", "excel") that would otherwise produce false positives in prose.
_CASE_SENSITIVE_SKILLS = {"C", "R", "Go", "Excel"}


def _skill_pairs() -> List[Tuple[str, str]]:
    """(pattern text, canonical name) for every skill and its variants."""
    pairs: List[Tuple[str, str]] = []
    for name in SKILL_PATTERNS:
        pairs.append((name, name))
        pairs.extend((variant, name) for variant in _SKILL_VARIANTS.get(name, []))
    # Longest first: at a given position the most specific name must be tried
    # before its prefixes ("JavaScript" before "Java", "C++" before "C").
    return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)


def _compile(patterns: Sequence[str], flags: int = 0) -> "re.Pattern[str]":
    """Build one regex from skill names.

    Uses lookarounds instead of ``\\b`` because ``\\b`` fails after non-word
    characters ("C++", "CI/CD" would never match).
    """
    alternatives = "|".join(re.escape(p) for p in sorted(patterns, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", flags)


_PAIRS = _skill_pairs()
_SENSITIVE_PAIRS = [p for p in _PAIRS if p[0] in _CASE_SENSITIVE_SKILLS]
_INSENSITIVE_PAIRS = [p for p in _PAIRS if p[0] not in _CASE_SENSITIVE_SKILLS]

_SKILL_RE = _compile([p[0] for p in _SENSITIVE_PAIRS])
_SKILL_RE_CI = _compile([p[0] for p in _INSENSITIVE_PAIRS], re.IGNORECASE)

_CANONICAL = dict(_SENSITIVE_PAIRS)
_CANONICAL_CI = {text.lower(): name for text, name in _INSENSITIVE_PAIRS}


def extract_skills_from_text(text: str, section: str) -> List[dict]:
    """Find skill mentions inside one section's text.

    Returns one dict per occurrence::

        {"raw_text": <as written>, "skill_name": <canonical>, "section": <section>}
    """
    if not text:
        return []

    found: List[Tuple[int, int, str, str]] = []
    for match in _SKILL_RE.finditer(text):
        raw = match.group(0)
        found.append((match.start(), match.end(), raw, _CANONICAL[raw]))
    for match in _SKILL_RE_CI.finditer(text):
        raw = match.group(0)
        found.append((match.start(), match.end(), raw, _CANONICAL_CI[raw.lower()]))

    # Longest match wins when patterns start at the same position.
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    results: List[dict] = []
    covered_until = -1
    for start, end, raw, canonical in found:
        if start < covered_until:
            continue  # nested inside an already-kept match ("C" inside "C++")
        covered_until = end
        results.append({"raw_text": raw, "skill_name": canonical, "section": section})
    return results


def assign_confidence(skill: str, section: str) -> str:
    """Rate a skill mention based on where it appears.

    - High:   Experience or Projects — hands-on evidence in context
    - Medium: Skills section — explicitly self-declared
    - Low:    anywhere else (summary, education, one-off mentions)
    """
    if not skill:
        return "Low"
    location = (section or "").strip().lower()
    if "experience" in location or "project" in location:
        return "High"
    if "skill" in location or "competenc" in location or "technolog" in location:
        return "Medium"
    return "Low"


def extract_all_skills(sections_dict: Dict[str, str]) -> List[dict]:
    """Run extraction over every section, attaching a confidence to each hit.

    ``sections_dict`` maps section name -> section text (as produced by
    ``resume_parser.parse_resume`` / ``detect_sections``).
    """
    skills: List[dict] = []
    for section, text in (sections_dict or {}).items():
        if not text:
            continue
        for skill in extract_skills_from_text(text, section):
            skill["confidence"] = assign_confidence(skill["skill_name"], section)
            skills.append(skill)
    return skills

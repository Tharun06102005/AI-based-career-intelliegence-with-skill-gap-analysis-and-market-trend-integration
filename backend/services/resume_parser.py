"""Resume document parsing: extract text from PDF/DOCX and detect sections.

Section detection is line-based and heading-driven: a line that normalizes to a
known heading alias (e.g. "SKILLS:", "• Technical Skills") starts a new section
that runs until the next heading. Returns only the sections that were found, in
document order.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypedDict

import fitz  # PyMuPDF
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


class ParsedResume(TypedDict):
    """Structured result returned by :func:`parse_resume`."""

    raw_text: str
    cleaned_text: str
    sections: Dict[str, str]


SECTION_NAMES: Tuple[str, ...] = (
    "Summary",
    "Skills",
    "Experience",
    "Projects",
    "Education",
    "Certifications",
)

# Normalised heading text (lowercase, bullets/numbering stripped) -> section.
_HEADING_ALIASES: Dict[str, str] = {
    # Summary / objective
    "summary": "Summary",
    "professional summary": "Summary",
    "career summary": "Summary",
    "profile summary": "Summary",
    "profile": "Summary",
    "objective": "Summary",
    "career objective": "Summary",
    "personal profile": "Summary",
    "about me": "Summary",
    # Skills
    "skills": "Skills",
    "technical skills": "Skills",
    "key skills": "Skills",
    "core skills": "Skills",
    "programming skills": "Skills",
    "skillset": "Skills",
    "skill set": "Skills",
    "technical skillset": "Skills",
    "skills & tools": "Skills",
    "skills and tools": "Skills",
    "skills & expertise": "Skills",
    "technologies": "Skills",
    "tech stack": "Skills",
    "core competencies": "Skills",
    "competencies": "Skills",
    "expertise": "Skills",
    # Experience
    "experience": "Experience",
    "work experience": "Experience",
    "professional experience": "Experience",
    "employment history": "Experience",
    "work history": "Experience",
    "career history": "Experience",
    "career experience": "Experience",
    "internships": "Experience",
    # Projects
    "projects": "Projects",
    "personal projects": "Projects",
    "academic projects": "Projects",
    "key projects": "Projects",
    "selected projects": "Projects",
    # Education
    "education": "Education",
    "academic background": "Education",
    "qualifications": "Education",
    "academic qualifications": "Education",
    "education & training": "Education",
    "education & certifications": "Education",
    # Certifications
    "certifications": "Certifications",
    "certification": "Certifications",
    "certificates": "Certifications",
    "professional certifications": "Certifications",
    "licenses": "Certifications",
    "licenses & certifications": "Certifications",
    "certifications & licenses": "Certifications",
    "certifications & awards": "Certifications",
    "certifications & training": "Certifications",
    "courses": "Certifications",
    "awards": "Certifications",
}

# Leading bullets/numbering (e.g. "1. ", "• ", "- ") removed from headings.
_LEADING_NOISE = re.compile(r"^[\s\d)*(.\-–—•·]+")


def parse_pdf(file_path: Path | str) -> str:
    """Extract raw text from a PDF, one page after another (PyMuPDF)."""
    document = fitz.open(str(file_path))
    try:
        return "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()


def parse_docx(file_path: Path | str) -> str:
    """Extract raw text from a DOCX file, keeping paragraphs and tables in order."""
    document = Document(str(file_path))
    blocks: List[str] = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            blocks.append(Paragraph(child, document).text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                blocks.append(" | ".join(cell for cell in cells if cell))
    return "\n".join(blocks)


def clean_text(text: str) -> str:
    """Normalise unicode and whitespace while keeping the line structure.

    - NFKC unicode normalisation (ligatures, fullwidth forms, NBSP, ...)
    - strips zero-width characters
    - unified line endings
    - trims each line, collapses runs of spaces/tabs
    - collapses blank-line runs to a single blank line
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)

    lines: List[str] = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u00a0]+", " ", line).strip()
        if not line and (not lines or lines[-1] == ""):
            continue  # drop leading blanks, collapse blank runs
        lines.append(line)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _normalize_heading(line: str) -> str:
    """Lowercase a heading candidate and strip bullets, numbering, punctuation."""
    cleaned = _LEADING_NOISE.sub("", line.strip().lower())
    cleaned = cleaned.rstrip(" \t:;.-–—•·*")
    return re.sub(r"\s+", " ", cleaned)


def detect_sections(text: str) -> Dict[str, str]:
    """Split resume text into sections keyed by canonical section name.

    Recognised headings: Summary, Skills, Experience, Projects, Education and
    Certifications (plus their common aliases). A heading may be a whole line
    ("SKILLS") or carry inline content ("Skills: Python, Java"). Text before the
    first heading (name/contact block) is ignored. Returns only the sections
    found, in document order — an empty dict when no headings match.
    """
    sections: Dict[str, str] = {}
    current: Optional[str] = None
    buffer: List[str] = []

    def flush() -> None:
        nonlocal buffer
        if current is None:
            buffer = []
            return
        body = "\n".join(buffer).strip()
        existing = sections.get(current, "")
        sections[current] = f"{existing}\n{body}".strip() if existing else body
        buffer = []

    for line in text.split("\n"):
        stripped = line.strip()

        if not stripped:
            if current is not None:
                buffer.append("")
            continue

        head, sep, rest = stripped.partition(":")
        section_name = _HEADING_ALIASES.get(_normalize_heading(head))

        if section_name is not None:
            flush()
            current = section_name
            if sep and rest.strip():
                buffer.append(rest.strip())
            continue

        if current is None:
            continue  # preamble (name/contact info) — belongs to no section
        buffer.append(stripped)

    flush()
    return sections


def parse_resume(file_path: Path | str) -> ParsedResume:
    """Parse a ``.pdf``/``.docx`` resume into raw text, cleaned text, sections.

    Raises:
        ValueError: if the file extension is not ``.pdf`` or ``.docx``.
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        raw_text = parse_pdf(path)
    elif extension == ".docx":
        raw_text = parse_docx(path)
    else:
        raise ValueError(
            f"Unsupported resume file type {extension!r}; expected '.pdf' or '.docx'"
        )

    cleaned_text = clean_text(raw_text)
    sections = detect_sections(cleaned_text)
    if not sections and cleaned_text.strip():
        # No headings recognised — keep the content as one block so downstream
        # skill extraction still sees it.
        sections = {"Other": cleaned_text}

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "sections": sections,
    }


def score_resume(
    sections: Dict[str, str] | List[str] | None = None,
    skills: List[Any] | None = None,
    raw_text: str = "",
) -> Dict[str, Any]:
    """Calculate structured Resume Score Card out of 100 points based on key section presence.

    Scoring:
      Education: 20 points
      Experience/Projects: 25 points
      Skills: 20 points
      Summary/Objective: 10 points
      Certifications: 10 points
      Contact Info: 15 points
    """
    sections = sections or {}
    skills = skills or []

    if isinstance(sections, dict):
        section_keys = {str(k).lower().strip() for k in sections.keys()}
        combined_text = (raw_text + " " + " ".join(str(v) for v in sections.values())).lower()
    elif isinstance(sections, (list, tuple, set)):
        section_keys = {str(k).lower().strip() for k in sections}
        combined_text = (raw_text + " " + " ".join(section_keys)).lower()
    else:
        section_keys = set()
        combined_text = raw_text.lower()

    # Education (20 pts)
    has_education = any(
        k in section_keys for k in ["education", "academic", "degree", "university", "college"]
    ) or bool(re.search(r"\b(bachelor|master|b\.s|m\.s|phd|degree|gpa|university|college)\b", combined_text))

    # Experience / Projects (25 pts)
    has_exp = any(
        k in section_keys
        for k in ["experience", "projects", "project", "work experience", "employment", "work history"]
    ) or bool(re.search(r"\b(experience|worked at|responsibilities|engineered|developed|built)\b", combined_text))

    # Skills (20 pts)
    has_skills = any(
        k in section_keys for k in ["skills", "technical skills", "core competencies", "technologies"]
    ) or len(skills) >= 3

    # Summary / Objective (10 pts)
    has_summary = any(
        k in section_keys for k in ["summary", "objective", "professional summary", "profile", "about me"]
    )

    # Certifications (10 pts)
    has_certs = any(
        k in section_keys for k in ["certifications", "certificates", "credentials", "licenses", "courses"]
    ) or bool(re.search(r"\b(certified|certification|aws certified|license)\b", combined_text))

    # Contact Info (15 pts)
    has_contact = any(
        k in section_keys for k in ["contact", "personal", "contact info", "preamble"]
    ) or bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", combined_text)) or bool(
        re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", combined_text)
    ) or bool(re.search(r"(linkedin\.com|github\.com)", combined_text))

    score = 0
    found: List[str] = []
    missing: List[str] = []
    tips: List[str] = []

    if has_education:
        score += 20
        found.append("Education")
    else:
        missing.append("Education")
        tips.append("Add an Education section highlighting your degree, institution, and graduation year.")

    if has_exp:
        score += 25
        found.append("Experience/Projects")
    else:
        missing.append("Experience/Projects")
        tips.append("Add an Experience or Projects section detailing your work history and technical deliverables.")

    if has_skills:
        score += 20
        found.append("Skills")
    else:
        missing.append("Skills")
        tips.append("Add a dedicated Skills section categorizing technical proficiencies, frameworks, and developer tools.")

    if has_summary:
        score += 10
        found.append("Summary/Objective")
    else:
        missing.append("Summary/Objective")
        tips.append("Add a 2-3 sentence Professional Summary at the top emphasizing your background and career goals.")

    if has_certs:
        score += 10
        found.append("Certifications")
    else:
        missing.append("Certifications")
        tips.append("Add relevant Certifications or completed coursework (e.g. AWS, CKA, Coursera) to demonstrate continuous learning.")

    if has_contact:
        score += 15
        found.append("Contact Info")
    else:
        missing.append("Contact Info")
        tips.append("Ensure your email, phone number, location, and LinkedIn / GitHub profile links are clearly visible at the top.")

    # Grade
    if score >= 85:
        grade = "A"
        if not tips:
            tips.append("Your resume structure is outstanding! Ensure achievements include quantifiable impact and metrics.")
    elif score >= 70:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    return {
        "total_score": score,
        "grade": grade,
        "sections_found": found,
        "sections_missing": missing,
        "tips": tips,
    }


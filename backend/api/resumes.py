"""Resume endpoints: upload a PDF/DOCX, run the pipeline, fetch results.

Pipeline: save upload -> ``parse_resume`` -> ``extract_all_skills`` ->
``normalize_all_skills`` -> persist ``resumes`` / ``resume_sections`` /
``profile_skills`` rows.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.auth import get_current_user
from core.config import PROJECT_ROOT
from models.database import Profile, ProfileSkill, Resume, ResumeSection, Skill, User
from models.session import get_db
from schemas.resume import (
    ATSCheckRequest,
    ATSCheckResponse,
    ResumeDetailResponse,
    ResumeUploadResponse,
)
from services.ats_scorer import calculate_ats_score
from services.resume_parser import parse_resume
from services.skill_extractor import extract_all_skills
from services.skill_normalizer import normalize_all_skills

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

UPLOAD_DIR = PROJECT_ROOT / "data" / "raw" / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

# Human-readable confidence labels stored as floats (ProfileSkill.confidence).
CONFIDENCE_SCORES = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _score(confidence: object) -> float:
    """Confidence label ("High") -> float for storage."""
    return CONFIDENCE_SCORES.get(str(confidence or "").strip().lower(), 0.0)


def _label(score: Optional[float]) -> Optional[str]:
    """Stored float confidence -> label for API responses."""
    if score is None:
        return None
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def _evidence(item: dict) -> str:
    """JSON evidence blob (section + excerpt) for ProfileSkill.evidence_ref."""
    payload = {
        "section": item.get("section"),
        "raw_text": (item.get("raw_text") or "")[:200],
    }
    return json.dumps(payload, ensure_ascii=False)


def _parse_evidence(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Inverse of :func:`_evidence`; tolerates legacy/plain-text values."""
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data.get("section"), data.get("raw_text")
    except (TypeError, ValueError):
        pass
    return None, None


def _get_or_create_profile(db: Session, user: User) -> Profile:
    """Fetch the user's profile, creating an empty one on first upload."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


def _upsert_skill(db: Session, canonical_name: str) -> Skill:
    skill = db.query(Skill).filter(Skill.canonical_name == canonical_name).first()
    if skill is None:
        skill = Skill(canonical_name=canonical_name)
        db.add(skill)
        db.flush()
    return skill


def _upsert_profile_skill(db: Session, profile_id: UUID, skill: Skill, item: dict) -> None:
    """Insert (or raise the confidence of) a profile_skill row."""
    score = _score(item.get("confidence"))
    existing = db.get(ProfileSkill, (profile_id, skill.id))
    if existing is None:
        db.add(
            ProfileSkill(
                profile_id=profile_id,
                skill_id=skill.id,
                confidence=score,
                evidence_ref=_evidence(item),
            )
        )
    elif score > (existing.confidence or 0.0):
        existing.confidence = score
        existing.evidence_ref = _evidence(item)


@router.post("", response_model=ResumeUploadResponse, status_code=201)
@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a resume, run parse -> extract -> normalize, persist results."""
    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    save_path.write_bytes(content)

    try:
        parsed = parse_resume(save_path)
        skills = normalize_all_skills(extract_all_skills(parsed["sections"]))
    except Exception as exc:  # corrupt/undecodable file -> client error
        raise HTTPException(status_code=400, detail=f"Could not parse resume: {exc}")

    profile = _get_or_create_profile(db, user)

    resume = Resume(
        profile_id=profile.id,
        file_ref=str(save_path.relative_to(PROJECT_ROOT)),
        original_filename=original_name,
        status="parsed",
    )
    db.add(resume)
    db.flush()  # assigns resume.id

    for position, (section_type, text) in enumerate(parsed["sections"].items()):
        db.add(
            ResumeSection(
                resume_id=resume.id,
                section_type=section_type,
                text=text,
                position=position,
            )
        )

    for item in skills:
        skill = _upsert_skill(db, item["skill_name"])
        _upsert_profile_skill(db, profile.id, skill, item)

    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "status": resume.status,
        "skills_count": len(skills),
        "sections_found": list(parsed["sections"]),
        "skills": [
            {
                "skill_name": item["skill_name"],
                "confidence": item.get("confidence"),
                "section": item.get("section"),
                "raw_text": item.get("raw_text"),
            }
            for item in skills
        ],
    }


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return one resume with its sections and extracted skills (owner only)."""
    resume = db.get(Resume, resume_id)
    if resume is None or resume.profile is None or resume.profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    rows = (
        db.query(ProfileSkill, Skill)
        .join(Skill, ProfileSkill.skill_id == Skill.id)
        .filter(ProfileSkill.profile_id == resume.profile_id)
        .order_by(Skill.canonical_name)
        .all()
    )

    skills: List[Dict[str, object]] = []
    for profile_skill, skill in rows:
        section, raw_text = _parse_evidence(profile_skill.evidence_ref)
        skills.append(
            {
                "skill_name": skill.canonical_name,
                "confidence": _label(profile_skill.confidence),
                "section": section,
                "raw_text": raw_text,
                "is_verified": bool(getattr(profile_skill, "is_verified", False)),
                "verified_score": getattr(profile_skill, "verified_score", None),
                "verified_level": getattr(profile_skill, "verified_level", None),
            }
        )

    return {
        "resume_id": resume.id,
        "filename": resume.original_filename,
        "status": resume.status,
        "uploaded_at": resume.uploaded_at,
        "sections": {s.section_type: (s.text or "") for s in resume.sections},
        "skills": skills,
    }


@router.post("/ats-check", response_model=ATSCheckResponse)
def ats_check(
    payload: ATSCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Calculate ATS score by comparing a candidate's resume to a job description."""
    resume_text = payload.resume_text or ""

    if payload.resume_id:
        resume = db.get(Resume, payload.resume_id)
        if resume and resume.profile and resume.profile.user_id == user.id:
            sections_text = "\n\n".join(s.text or "" for s in resume.sections if s.text)
            if sections_text.strip():
                resume_text = (
                    sections_text
                    if not resume_text.strip()
                    else f"{resume_text}\n\n{sections_text}"
                )

    if not resume_text.strip():
        # Fallback to latest resume of the user
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if profile and profile.resumes:
            latest_resume = profile.resumes[-1]
            sections_text = "\n\n".join(s.text or "" for s in latest_resume.sections if s.text)
            if sections_text.strip():
                resume_text = sections_text

    result = calculate_ats_score(resume_text, payload.job_description)
    return result

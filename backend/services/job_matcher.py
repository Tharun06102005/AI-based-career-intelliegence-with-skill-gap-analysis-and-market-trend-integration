"""Job and Internship Matching Engine.

Provides:
- Deduplication and normalized ingestion (CSV import, manual posting, verified feeds)
- Transparent matching score formula based on verified skills, experience, and eligibility
- Breakdown of matched vs verified skills, missing skills, and match explanations
- Application status lifecycle tracking (Saved, Applied, Assessment, Interview, Offer, Rejected)
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from sqlalchemy.orm import Session

from models.database import (
    CareerRole,
    JobOpportunity,
    Profile,
    ProfileSkill,
    UserOpportunity,
)
from services.skill_normalizer import normalize_skill

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Curated Verified & Sample Opportunities
# -----------------------------------------------------------------------------
CURATED_OPPORTUNITIES: List[Dict[str, Any]] = [
    {
        "source": "verified_partner",
        "source_id": "opp-swe-int-01",
        "normalized_url": "https://careers.google.com/jobs/results/swe-intern-2025",
        "title": "Software Engineering Intern - Summer 2025",
        "company_name": "Google",
        "location": "Mountain View, CA / Remote",
        "work_mode": "Hybrid",
        "opportunity_type": "Internship",
        "experience_level": "Entry Level",
        "min_salary": 52.0,
        "max_salary": 62.0,
        "currency": "USD/hr",
        "description": "Join Google's engineering team to build scalable systems, web infrastructure, and innovative developer tools. You will write high-quality code in Python, C++, or Java.",
        "required_skills": ["Python", "SQL", "Git", "Data Structures"],
        "preferred_skills": ["Docker", "Linux", "REST APIs"],
        "eligibility_criteria": {"education": "Bachelor's or Master's in CS or related field", "grad_year": "2025-2026"},
        "application_url": "https://careers.google.com/jobs/results/swe-intern-2025",
        "is_verified": True,
    },
    {
        "source": "verified_partner",
        "source_id": "opp-backend-jr-02",
        "normalized_url": "https://stripe.com/jobs/listings/junior-backend-engineer",
        "title": "Junior Backend Engineer",
        "company_name": "Stripe",
        "location": "San Francisco, CA / Remote",
        "work_mode": "Remote",
        "opportunity_type": "Full-time",
        "experience_level": "Junior",
        "min_salary": 125000.0,
        "max_salary": 155000.0,
        "currency": "USD",
        "description": "Design and build mission-critical payment infrastructure, high-throughput microservices, and reliable RESTful APIs using Python, PostgreSQL, and Redis.",
        "required_skills": ["Python", "SQL", "REST APIs", "PostgreSQL"],
        "preferred_skills": ["Docker", "Redis", "Microservices", "Kafka"],
        "eligibility_criteria": {"experience": "0-2 years software development experience"},
        "application_url": "https://stripe.com/jobs/listings/junior-backend-engineer",
        "is_verified": True,
    },
    {
        "source": "verified_partner",
        "source_id": "opp-frontend-jr-03",
        "normalized_url": "https://vercel.com/careers/frontend-engineer-nextjs",
        "title": "Frontend Engineer - Developer Experience",
        "company_name": "Vercel",
        "location": "Remote",
        "work_mode": "Remote",
        "opportunity_type": "Full-time",
        "experience_level": "Junior",
        "min_salary": 115000.0,
        "max_salary": 140000.0,
        "currency": "USD",
        "description": "Help create world-class developer interfaces with Next.js, React, TypeScript, and modern CSS tooling. Collaborate closely with designers and product engineers.",
        "required_skills": ["React", "TypeScript", "JavaScript", "HTML", "CSS"],
        "preferred_skills": ["Next.js", "Tailwind", "Git", "REST APIs"],
        "eligibility_criteria": {"experience": "1+ years web frontend development"},
        "application_url": "https://vercel.com/careers/frontend-engineer-nextjs",
        "is_verified": True,
    },
    {
        "source": "imported_dataset",
        "source_id": "opp-ds-int-04",
        "normalized_url": "https://meta.com/careers/data-science-intern",
        "title": "Data Science & Analytics Intern",
        "company_name": "Meta",
        "location": "Menlo Park, CA / Hybrid",
        "work_mode": "Hybrid",
        "opportunity_type": "Internship",
        "experience_level": "Entry Level",
        "min_salary": 50.0,
        "max_salary": 58.0,
        "currency": "USD/hr",
        "description": "Analyze large-scale behavioral data, design experiment metrics (A/B testing), and extract actionable statistical insights with SQL, Python, and Pandas.",
        "required_skills": ["Python", "SQL", "Pandas", "Statistics"],
        "preferred_skills": ["Scikit-learn", "Tableau", "Machine Learning"],
        "eligibility_criteria": {"education": "Pursuing degree in Quantitative discipline, CS, Math, or Stats"},
        "application_url": "https://meta.com/careers/data-science-intern",
        "is_verified": False,
    },
    {
        "source": "verified_partner",
        "source_id": "opp-fullstack-05",
        "normalized_url": "https://github.com/about/careers/fullstack-developer",
        "title": "Associate Full Stack Developer",
        "company_name": "GitHub",
        "location": "Remote",
        "work_mode": "Remote",
        "opportunity_type": "Full-time",
        "experience_level": "Junior",
        "min_salary": 110000.0,
        "max_salary": 135000.0,
        "currency": "USD",
        "description": "Deliver end-to-end features supporting millions of developers worldwide. Work with React, TypeScript, Python backend services, and Git workflows.",
        "required_skills": ["React", "Python", "JavaScript", "SQL", "Git"],
        "preferred_skills": ["Docker", "REST APIs", "Node.js", "CI/CD"],
        "eligibility_criteria": {"experience": "0-2 years full stack web experience"},
        "application_url": "https://github.com/about/careers/fullstack-developer",
        "is_verified": True,
    },
    {
        "source": "imported_dataset",
        "source_id": "opp-devops-06",
        "normalized_url": "https://aws.amazon.com/careers/cloud-devops-engineer",
        "title": "Cloud Support & DevOps Associate",
        "company_name": "Amazon Web Services (AWS)",
        "location": "Seattle, WA / Hybrid",
        "work_mode": "Hybrid",
        "opportunity_type": "Full-time",
        "experience_level": "Junior",
        "min_salary": 118000.0,
        "max_salary": 142000.0,
        "currency": "USD",
        "description": "Support reliable cloud infrastructures, automate deployments, and configure container workloads using Docker, Linux, CI/CD, and AWS services.",
        "required_skills": ["Linux", "Docker", "AWS", "Git"],
        "preferred_skills": ["Kubernetes", "CI/CD", "Python", "Terraform"],
        "eligibility_criteria": {"experience": "0-2 years systems or cloud experience"},
        "application_url": "https://aws.amazon.com/careers/cloud-devops-engineer",
        "is_verified": False,
    },
]


def normalize_opportunity_url(url: Optional[str]) -> Optional[str]:
    """Strip tracking queries (utm_*, ref, etc.) and standardize URL structure."""
    if not url or not url.strip():
        return None

    parsed = urlparse(url.strip())
    # Clean tracking query parameters
    filtered_queries = [
        (k, v) for k, v in parse_qsl(parsed.query)
        if not k.lower().startswith("utm_") and k.lower() not in ("ref", "fbclid", "gclid")
    ]
    clean_query = urlencode(filtered_queries)
    clean_path = parsed.path.rstrip("/").lower()
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), clean_path, parsed.params, clean_query, ""))


def seed_job_opportunities(db: Session) -> int:
    """Populate database with curated job and internship opportunities if empty."""
    existing_count = db.query(JobOpportunity).count()
    if existing_count > 0:
        return existing_count

    inserted = 0
    for opp in CURATED_OPPORTUNITIES:
        norm_url = normalize_opportunity_url(opp.get("application_url"))
        job = JobOpportunity(
            source=opp["source"],
            source_id=opp["source_id"],
            normalized_url=norm_url,
            title=opp["title"],
            company_name=opp["company_name"],
            location=opp.get("location"),
            work_mode=opp.get("work_mode", "Remote"),
            opportunity_type=opp.get("opportunity_type", "Full-time"),
            experience_level=opp.get("experience_level", "Junior"),
            min_salary=opp.get("min_salary"),
            max_salary=opp.get("max_salary"),
            currency=opp.get("currency", "USD"),
            description=opp.get("description"),
            required_skills=opp.get("required_skills", []),
            preferred_skills=opp.get("preferred_skills", []),
            eligibility_criteria=opp.get("eligibility_criteria", {}),
            application_url=opp.get("application_url"),
            is_verified=opp.get("is_verified", False),
            date_posted=datetime.utcnow(),
            last_verified_at=datetime.utcnow(),
        )
        db.add(job)
        inserted += 1

    db.commit()
    logger.info("Seeded %d job opportunities into database.", inserted)
    return inserted


def calculate_opportunity_match(
    profile_skills: List[Dict[str, Any]],
    opportunity: JobOpportunity,
    candidate_experience_years: float = 1.0,
    preferred_work_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Transparent matching formula for a candidate profile against a job opportunity.

    Formula:
        MatchScore = 0.50 * SkillMatch
                   + 0.20 * ExperienceMatch
                   + 0.15 * PreferredSkillMatch
                   + 0.10 * WorkModeMatch
                   + 0.05 * VerificationBonus

    Returns:
        total_score (0-100), matched_skills, verified_matched_skills,
        missing_skills, eligibility_concerns, and match_reasons.
    """
    req_skills = opportunity.required_skills if isinstance(opportunity.required_skills, list) else []
    pref_skills = opportunity.preferred_skills if isinstance(opportunity.preferred_skills, list) else []

    # Map candidate skills for fast matching
    candidate_skill_map: Dict[str, Dict[str, Any]] = {}
    for ps in profile_skills:
        name = str(ps.get("skill_name", "")).strip().lower()
        if name:
            candidate_skill_map[name] = ps
            norm = normalize_skill(name).strip().lower()
            if norm:
                candidate_skill_map[norm] = ps

    matched_skills: List[str] = []
    verified_matched_skills: List[str] = []
    missing_skills: List[str] = []

    for s in req_skills:
        s_clean = s.strip().lower()
        s_norm = normalize_skill(s).strip().lower()

        ps_match = candidate_skill_map.get(s_clean) or candidate_skill_map.get(s_norm)
        if ps_match:
            matched_skills.append(s)
            if ps_match.get("is_verified"):
                verified_matched_skills.append(s)
        else:
            missing_skills.append(s)

    # 1. Skill Match Component (0.0 to 1.0)
    skill_match = len(matched_skills) / len(req_skills) if req_skills else 1.0

    # 2. Preferred Skills Match Component (0.0 to 1.0)
    matched_pref = [s for s in pref_skills if (s.lower() in candidate_skill_map or normalize_skill(s).lower() in candidate_skill_map)]
    pref_match = len(matched_pref) / len(pref_skills) if pref_skills else 0.5

    # 3. Experience Match Component
    exp_level = (opportunity.experience_level or "Entry Level").lower()
    if "entry" in exp_level or "intern" in exp_level:
        exp_match = 1.0
    elif "junior" in exp_level:
        exp_match = 1.0 if candidate_experience_years >= 0.5 else 0.7
    elif "mid" in exp_level:
        exp_match = 1.0 if candidate_experience_years >= 2.0 else 0.5
    else:  # Senior
        exp_match = 1.0 if candidate_experience_years >= 5.0 else 0.3

    # 4. Work Mode Match Component
    if preferred_work_mode:
        work_match = 1.0 if preferred_work_mode.lower() == opportunity.work_mode.lower() or opportunity.work_mode.lower() == "remote" else 0.6
    else:
        work_match = 0.9

    # 5. Verification Bonus
    verification_bonus = (len(verified_matched_skills) / len(req_skills)) if req_skills else 0.0

    raw_score = (
        0.50 * skill_match
        + 0.20 * exp_match
        + 0.15 * pref_match
        + 0.10 * work_match
        + 0.05 * verification_bonus
    )

    total_score = round(min(100.0, max(0.0, raw_score * 100.0)), 1)

    # Compile match reasons
    reasons = []
    if skill_match >= 0.7:
        reasons.append(f"Strong overlap with core required skills ({len(matched_skills)}/{len(req_skills)} matched).")
    if verified_matched_skills:
        reasons.append(f"Includes {len(verified_matched_skills)} assessment-verified skill(s): {', '.join(verified_matched_skills)}.")
    if matched_pref:
        reasons.append(f"Matches preferred stack: {', '.join(matched_pref)}.")
    if opportunity.work_mode == "Remote":
        reasons.append("Remote flexibility offers seamless access without relocation.")

    eligibility_concerns = []
    if missing_skills:
        eligibility_concerns.append(f"Missing {len(missing_skills)} required skill(s): {', '.join(missing_skills)}.")
    if exp_match < 0.7:
        eligibility_concerns.append(f"Role requires {opportunity.experience_level} experience.")

    return {
        "opportunity_id": opportunity.id,
        "match_score": total_score,
        "matched_skills": matched_skills,
        "verified_matched_skills": verified_matched_skills,
        "missing_skills": missing_skills,
        "matched_preferred_skills": matched_pref,
        "eligibility_concerns": eligibility_concerns,
        "match_reasons": reasons,
    }


def get_matched_opportunities(
    profile_id: UUID,
    db: Session,
    opportunity_type: Optional[str] = None,
    work_mode: Optional[str] = None,
    min_salary: Optional[float] = None,
    search_query: Optional[str] = None,
    sort_by: str = "match_score",  # match_score, date_posted, salary
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Fetch opportunities matched and ranked for the candidate profile."""
    seed_job_opportunities(db)

    # 1. Load candidate profile skills
    profile_skills_records = (
        db.query(ProfileSkill)
        .filter(ProfileSkill.profile_id == profile_id)
        .join(ProfileSkill.skill)
        .all()
    )

    profile_skills = [
        {
            "skill_name": ps.skill.canonical_name,
            "confidence": ps.confidence,
            "is_verified": ps.is_verified,
            "verified_score": ps.verified_score,
        }
        for ps in profile_skills_records
    ]

    # 2. Query opportunities with filters
    query = db.query(JobOpportunity)

    if opportunity_type and opportunity_type.lower() != "all":
        query = query.filter(JobOpportunity.opportunity_type.ilike(opportunity_type))

    if work_mode and work_mode.lower() != "all":
        query = query.filter(JobOpportunity.work_mode.ilike(work_mode))

    if min_salary is not None:
        query = query.filter(JobOpportunity.min_salary >= min_salary)

    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        query = query.filter(
            (JobOpportunity.title.ilike(term)) | (JobOpportunity.company_name.ilike(term)) | (JobOpportunity.description.ilike(term))
        )

    all_opps = query.all()

    # 3. Load user tracked application statuses
    user_apps = {
        uo.opportunity_id: uo.status
        for uo in db.query(UserOpportunity)
        .filter(UserOpportunity.profile_id == profile_id)
        .all()
    }

    # 4. Calculate matches
    scored_opps = []
    for opp in all_opps:
        match_data = calculate_opportunity_match(profile_skills, opp)
        scored_opps.append({
            "id": opp.id,
            "title": opp.title,
            "company_name": opp.company_name,
            "location": opp.location,
            "work_mode": opp.work_mode,
            "opportunity_type": opp.opportunity_type,
            "experience_level": opp.experience_level,
            "min_salary": opp.min_salary,
            "max_salary": opp.max_salary,
            "currency": opp.currency,
            "description": opp.description,
            "required_skills": opp.required_skills,
            "preferred_skills": opp.preferred_skills,
            "eligibility_criteria": opp.eligibility_criteria,
            "application_url": opp.application_url,
            "is_verified": opp.is_verified,
            "source": opp.source,
            "date_posted": opp.date_posted.isoformat() if opp.date_posted else None,
            "application_status": user_apps.get(opp.id, None),
            **match_data,
        })

    # 5. Sorting
    if sort_by == "match_score":
        scored_opps.sort(key=lambda x: x["match_score"], reverse=True)
    elif sort_by == "date_posted":
        scored_opps.sort(key=lambda x: x["date_posted"] or "", reverse=True)
    elif sort_by == "salary":
        scored_opps.sort(key=lambda x: x["min_salary"] or 0, reverse=True)

    total_count = len(scored_opps)
    paginated = scored_opps[offset : offset + limit]

    return {
        "total_count": total_count,
        "opportunities": paginated,
    }


def update_application_status(
    profile_id: UUID,
    opportunity_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Optional[Session] = None,
) -> UserOpportunity:
    """Save or update candidate tracking status for an opportunity.

    Valid statuses: Saved, Applied, Assessment, Interview, Offer, Rejected
    """
    if db is None:
        raise ValueError("Database session required.")

    valid_statuses = {"Saved", "Applied", "Assessment", "Interview", "Offer", "Rejected"}
    formatted_status = status.capitalize() if status.capitalize() in valid_statuses else "Saved"

    entry = (
        db.query(UserOpportunity)
        .filter(
            UserOpportunity.profile_id == profile_id,
            UserOpportunity.opportunity_id == opportunity_id,
        )
        .first()
    )

    if entry:
        entry.status = formatted_status
        if notes is not None:
            entry.notes = notes
        if formatted_status == "Applied" and not entry.applied_at:
            entry.applied_at = datetime.utcnow()
        entry.updated_at = datetime.utcnow()
    else:
        entry = UserOpportunity(
            profile_id=profile_id,
            opportunity_id=opportunity_id,
            status=formatted_status,
            notes=notes,
            applied_at=datetime.utcnow() if formatted_status == "Applied" else None,
            updated_at=datetime.utcnow(),
        )
        db.add(entry)

    db.commit()
    db.refresh(entry)
    return entry


def get_tracked_applications(
    profile_id: UUID,
    db: Session,
) -> List[Dict[str, Any]]:
    """Retrieve all saved and active applications for a candidate profile."""
    entries = (
        db.query(UserOpportunity, JobOpportunity)
        .join(JobOpportunity, UserOpportunity.opportunity_id == JobOpportunity.id)
        .filter(UserOpportunity.profile_id == profile_id)
        .order_by(UserOpportunity.updated_at.desc())
        .all()
    )

    results = []
    for uo, opp in entries:
        results.append({
            "id": uo.id,
            "opportunity_id": opp.id,
            "title": opp.title,
            "company_name": opp.company_name,
            "location": opp.location,
            "work_mode": opp.work_mode,
            "opportunity_type": opp.opportunity_type,
            "status": uo.status,
            "notes": uo.notes,
            "applied_at": uo.applied_at.isoformat() if uo.applied_at else None,
            "updated_at": uo.updated_at.isoformat(),
            "application_url": opp.application_url,
            "is_verified": opp.is_verified,
        })
    return results


def import_opportunities_from_csv(
    csv_content: str,
    db: Session,
    source_label: str = "imported_csv",
) -> Dict[str, Any]:
    """Ingest opportunities from CSV text, normalizing titles, skills, and deduplicating URLs."""
    reader = csv.DictReader(io.StringIO(csv_content))
    inserted = 0
    skipped = 0

    for row in reader:
        title = row.get("title") or row.get("job_title") or ""
        company = row.get("company") or row.get("company_name") or ""
        if not title or not company:
            skipped += 1
            continue

        raw_url = row.get("url") or row.get("application_url") or row.get("source_url")
        norm_url = normalize_opportunity_url(raw_url)

        # Deduplication check
        if norm_url:
            existing = db.query(JobOpportunity).filter(JobOpportunity.normalized_url == norm_url).first()
            if existing:
                skipped += 1
                continue

        # Extract skills
        raw_skills_str = row.get("skills") or row.get("required_skills") or ""
        skills_list = [s.strip() for s in re.split(r"[,;]\s*", raw_skills_str) if s.strip()]

        opp = JobOpportunity(
            source=source_label,
            source_id=row.get("job_id") or row.get("id"),
            normalized_url=norm_url,
            title=title.strip(),
            company_name=company.strip(),
            location=row.get("location"),
            work_mode=row.get("work_mode", "Remote"),
            opportunity_type=row.get("opportunity_type", "Full-time"),
            experience_level=row.get("experience_level", "Junior"),
            min_salary=float(row["min_salary"]) if row.get("min_salary") else None,
            max_salary=float(row["max_salary"]) if row.get("max_salary") else None,
            currency=row.get("currency", "USD"),
            description=row.get("description"),
            required_skills=skills_list,
            preferred_skills=[],
            application_url=raw_url,
            is_verified=False,
            date_posted=datetime.utcnow(),
            last_verified_at=datetime.utcnow(),
        )
        db.add(opp)
        inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped}

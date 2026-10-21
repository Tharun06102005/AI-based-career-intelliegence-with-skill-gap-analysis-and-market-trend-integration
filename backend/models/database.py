# Database models created successfully
"""Complete SQLAlchemy 2.0 schema for the AI Career Intelligence System.

Defines all 20 tables with relationships, UUID primary keys where required,
indexed foreign keys, and JSON columns for scoring/simulation payloads.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all career-intelligence models."""


# ---------------------------------------------------------------------------
# 1. users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    profiles: Mapped[List["Profile"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 2. profiles
# ---------------------------------------------------------------------------
class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    education_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profiles")
    resumes: Mapped[List["Resume"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    profile_skills: Mapped[List["ProfileSkill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    career_scores: Mapped[List["CareerScore"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[List["SkillGap"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    progress_entries: Mapped[List["Progress"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    assessment_attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    saved_opportunities: Mapped[List["UserOpportunity"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 3. resumes
# ---------------------------------------------------------------------------
class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_ref: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="resumes")
    sections: Mapped[List["ResumeSection"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="ResumeSection.position"
    )


# ---------------------------------------------------------------------------
# 4. resume_sections
# ---------------------------------------------------------------------------
class ResumeSection(Base):
    __tablename__ = "resume_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="sections")


# ---------------------------------------------------------------------------
# 5. skills
# ---------------------------------------------------------------------------
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    aliases: Mapped[List["SkillAlias"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    profile_skills: Mapped[List["ProfileSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    career_skills: Mapped[List["CareerSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    job_skills: Mapped[List["JobSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[List["SkillGap"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    simulation_changes: Mapped[List["SimulationChange"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    resources: Mapped[List["Resource"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 6. skill_aliases
# ---------------------------------------------------------------------------
class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    skill: Mapped["Skill"] = relationship(back_populates="aliases")


# ---------------------------------------------------------------------------
# 7. profile_skills (composite key: profile_id + skill_id)
# ---------------------------------------------------------------------------
class ProfileSkill(Base):
    __tablename__ = "profile_skills"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_ref: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="profile_skills")
    skill: Mapped["Skill"] = relationship(back_populates="profile_skills")


# ---------------------------------------------------------------------------
# 8. career_roles
# ---------------------------------------------------------------------------
class CareerRole(Base):
    __tablename__ = "career_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    career_skills: Mapped[List["CareerSkill"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    metrics: Mapped[Optional["CareerMetric"]] = relationship(
        back_populates="career", cascade="all, delete-orphan", uselist=False
    )
    career_scores: Mapped[List["CareerScore"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[List["SkillGap"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 9. career_skills (composite key: career_id + skill_id)
# ---------------------------------------------------------------------------
class CareerSkill(Base):
    __tablename__ = "career_skills"

    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    importance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    career: Mapped["CareerRole"] = relationship(back_populates="career_skills")
    skill: Mapped["Skill"] = relationship(back_populates="career_skills")


# ---------------------------------------------------------------------------
# 10. jobs
# ---------------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_role: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job_skills: Mapped[List["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 11. job_skills (composite key: job_id + skill_id)
# ---------------------------------------------------------------------------
class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    job: Mapped["Job"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship(back_populates="job_skills")


# ---------------------------------------------------------------------------
# 12. career_metrics (career_id doubles as primary key)
# ---------------------------------------------------------------------------
class CareerMetric(Base):
    __tablename__ = "career_metrics"

    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    demand_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    job_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    career: Mapped["CareerRole"] = relationship(back_populates="metrics")


# ---------------------------------------------------------------------------
# 13. career_scores
# ---------------------------------------------------------------------------
class CareerScore(Base):
    __tablename__ = "career_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    components: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="career_scores")
    career: Mapped["CareerRole"] = relationship(back_populates="career_scores")


# ---------------------------------------------------------------------------
# 14. skill_gaps
# ---------------------------------------------------------------------------
class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    importance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="skill_gaps")
    career: Mapped["CareerRole"] = relationship(back_populates="skill_gaps")
    skill: Mapped["Skill"] = relationship(back_populates="skill_gaps")


# ---------------------------------------------------------------------------
# 15. simulations
# ---------------------------------------------------------------------------
class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    career_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="simulations")
    career: Mapped["CareerRole"] = relationship(back_populates="simulations")
    changes: Mapped[List["SimulationChange"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )
    results: Mapped[Optional["SimulationResult"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan", uselist=False
    )


# ---------------------------------------------------------------------------
# 16. simulation_changes
# ---------------------------------------------------------------------------
class SimulationChange(Base):
    __tablename__ = "simulation_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    simulation: Mapped["Simulation"] = relationship(back_populates="changes")
    skill: Mapped["Skill"] = relationship(back_populates="simulation_changes")


# ---------------------------------------------------------------------------
# 17. simulation_results
# ---------------------------------------------------------------------------
class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulations.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    baseline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    simulated: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    delta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    simulation: Mapped["Simulation"] = relationship(back_populates="results")


# ---------------------------------------------------------------------------
# 18. resources
# ---------------------------------------------------------------------------
class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    skill: Mapped["Skill"] = relationship(back_populates="resources")
    progress_entries: Mapped[List["Progress"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 19. progress
# ---------------------------------------------------------------------------
class Progress(Base):
    __tablename__ = "progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)
    progress: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    profile: Mapped["Profile"] = relationship(back_populates="progress_entries")
    resource: Mapped["Resource"] = relationship(back_populates="progress_entries")


# ---------------------------------------------------------------------------
# 20. evaluations
# ---------------------------------------------------------------------------
class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    metric: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# 21. assessment_questions
# ---------------------------------------------------------------------------
class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)  # Beginner, Intermediate, Advanced
    question_type: Mapped[str] = mapped_column(String(50), default="mcq", nullable=False)  # mcq, output, debugging, coding
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of choices for MCQ/output
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_cases: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of {input, expected_output, is_hidden}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    responses: Mapped[List["AssessmentResponse"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 22. assessment_attempts
# ---------------------------------------------------------------------------
class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="assessment_attempts")
    responses: Mapped[List["AssessmentResponse"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 23. assessment_responses
# ---------------------------------------------------------------------------
class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assessment_questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    attempt: Mapped["AssessmentAttempt"] = relationship(back_populates="responses")
    question: Mapped["AssessmentQuestion"] = relationship(back_populates="responses")


# ---------------------------------------------------------------------------
# 24. job_opportunities
# ---------------------------------------------------------------------------
class JobOpportunity(Base):
    __tablename__ = "job_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), default="imported", index=True, nullable=False)  # verified, imported, manual
    source_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    normalized_url: Mapped[Optional[str]] = mapped_column(String(1024), unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str] = mapped_column(String(50), default="Remote", nullable=False)  # Remote, Hybrid, On-site
    opportunity_type: Mapped[str] = mapped_column(String(50), default="Full-time", nullable=False)  # Full-time, Internship, Contract
    experience_level: Mapped[str] = mapped_column(String(50), default="Entry Level", nullable=False)  # Entry Level, Junior, Mid, Senior
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(20), default="USD", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    eligibility_criteria: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_applications: Mapped[List["UserOpportunity"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 25. user_opportunities
# ---------------------------------------------------------------------------
class UserOpportunity(Base):
    __tablename__ = "user_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_opportunities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="Saved", nullable=False)  # Saved, Applied, Assessment, Interview, Offer, Rejected
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    profile: Mapped["Profile"] = relationship(back_populates="saved_opportunities")
    opportunity: Mapped["JobOpportunity"] = relationship(back_populates="user_applications")


# ---------------------------------------------------------------------------
# 26. interview_sessions
# ---------------------------------------------------------------------------
class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    career_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True
    )
    role_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="technical", nullable=False)  # technical, coding, project_defense, resume_based, hr
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)  # in_progress, completed
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strengths: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    improvements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="interview_sessions")
    turns: Mapped[List["InterviewTurn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="InterviewTurn.turn_number"
    )


# ---------------------------------------------------------------------------
# 27. interview_turns
# ---------------------------------------------------------------------------
class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="technical", nullable=False)
    context_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluation_rubric: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_concepts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    example_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["InterviewSession"] = relationship(back_populates="turns")


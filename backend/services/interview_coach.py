"""AI Mock Interview Coach Service.

Provides:
- Role & resume-tailored interview practice (Technical, Coding, Project Defense, Resume-Based, HR)
- Adaptive question generation using candidate resume projects and target role gaps
- 5-metric rubric evaluation (Correctness, Completeness, Depth, Clarity, Relevance)
- Example strong answers, missing concepts, and revision topics
- Resilient fallback engine for Groq API outages
- Final session reports integrated with skill gap diagnostics
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from groq import Groq
from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.config import settings
from models.database import (
    CareerRole,
    InterviewSession,
    InterviewTurn,
    Profile,
    ProfileSkill,
    Resume,
    ResumeSection,
    SkillGap,
)
from services.skill_normalizer import normalize_skill

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODELS = ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]


# -----------------------------------------------------------------------------
# Curated Domain Interview Questions (Fallback & Standard Library)
# -----------------------------------------------------------------------------
FALLBACK_QUESTIONS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Software Engineer": {
        "technical": [
            {
                "question": "Can you explain how hash tables resolve collisions, and what is the difference between open addressing and chaining?",
                "context": "Core Data Structures & Algorithmic efficiency",
            },
            {
                "question": "How do you design a thread-safe singleton in your preferred programming language, and what issues can occur with double-checked locking?",
                "context": "Concurrent Programming & Design Patterns",
            },
        ],
        "project_defense": [
            {
                "question": "In the projects listed on your resume, what was the most difficult architectural bottleneck you encountered and how did you measure the performance improvement after refactoring?",
                "context": "Resume Project Architecture Defense",
            },
        ],
        "hr": [
            {
                "question": "Tell me about a time when you disagreed with a technical design decision proposed by a teammate. How did you resolve the conflict constructively?",
                "context": "Engineering Collaboration & Conflict Resolution",
            },
        ],
    },
    "Backend Developer": {
        "technical": [
            {
                "question": "Explain database indexing using B-Trees. When would an index degrade write performance, and how do composite indexes handle column order?",
                "context": "Database Optimization & Query Execution",
            },
            {
                "question": "What strategies do you use to ensure idempotency in REST APIs, specifically for payment processing or duplicate POST requests?",
                "context": "Distributed Systems & API Reliability",
            },
        ],
        "project_defense": [
            {
                "question": "How did you manage authentication and session persistence in your backend project? What tradeoffs did you consider between JWTs and server-side sessions?",
                "context": "Backend Project Security Defense",
            },
        ],
        "hr": [
            {
                "question": "Describe an incident where a production outage or critical bug occurred in your code. How did you handle the rollback and subsequent post-mortem?",
                "context": "Incident Management & Ownership",
            },
        ],
    },
    "Data Scientist": {
        "technical": [
            {
                "question": "How do you diagnose and address high variance (overfitting) versus high bias (underfitting) in machine learning models?",
                "context": "Statistical Learning Theory",
            },
            {
                "question": "When would you choose Precision over Recall as your primary evaluation metric, and how does the ROC-AUC curve behave with severe class imbalance?",
                "context": "Model Evaluation & Metric Engineering",
            },
        ],
        "project_defense": [
            {
                "question": "For the analytical or predictive project described in your resume, what validation strategy did you use to prevent data leakage during feature preprocessing?",
                "context": "Data Science Methodology Defense",
            },
        ],
        "hr": [
            {
                "question": "How do you communicate complex statistical models and probabilistic findings to non-technical business stakeholders?",
                "context": "Stakeholder Communication",
            },
        ],
    },
}


def _get_groq_client() -> Optional[Groq]:
    """Initialize Groq client if API key is configured."""
    key = getattr(settings, "GROQ_API_KEY", "") or ""
    if key and key != "your_groq_api_key_here":
        try:
            return Groq(api_key=key)
        except Exception as e:
            logger.warning("Failed to initialize Groq client: %s", e)
    return None


def extract_resume_projects_and_experience(profile_id: UUID, db: Session) -> Dict[str, str]:
    """Retrieve text from Projects and Experience sections of candidate's latest resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.profile_id == profile_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )

    extracted = {"projects": "", "experience": "", "skills": ""}
    if resume and resume.sections:
        for s in resume.sections:
            stype = (s.section_type or "").lower()
            if "project" in stype:
                extracted["projects"] += (s.text or "") + "\n"
            elif "experience" in stype:
                extracted["experience"] += (s.text or "") + "\n"
            elif "skill" in stype:
                extracted["skills"] += (s.text or "") + "\n"

    # Fallback to profile summaries if resume sections empty
    if not extracted["experience"] or not extracted["projects"]:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if profile:
            if profile.experience_summary:
                extracted["experience"] += profile.experience_summary
            if profile.education_summary:
                extracted["projects"] += profile.education_summary

    return extracted


def generate_interview_question(
    session_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Generate the next interview question tailored to role, category, and resume context."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError(f"Interview session {session_id} not found.")

    turn_count = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.session_id == session_id)
        .count()
    )

    turn_number = turn_count + 1

    # Extract resume context
    resume_context = extract_resume_projects_and_experience(session.profile_id, db)
    client = _get_groq_client()

    question_text = ""
    context_snippet = ""
    example_answer = ""

    if client:
        # Prompt Groq with candidate profile context
        prompt = f"""You are an elite senior technical hiring manager conducting a mock interview for the role of '{session.role_name}'.
Category: {session.category}
Difficulty: {session.difficulty}
Current Question Number: {turn_number}

Candidate's Resume Context:
- Projects: {resume_context['projects'][:800]}
- Experience: {resume_context['experience'][:600]}
- Skills Mentioned: {resume_context['skills'][:400]}

Generate Question #{turn_number}:
- If category is 'project_defense', ask a rigorous, specific question challenging technical design, architectural tradeoffs, or scalability of one of their actual resume projects!
- If category is 'technical' or 'coding', ask a practical question testing their core {session.role_name} skills.
- If category is 'hr', ask a behavioral question with STAR method expectations.

Return ONLY a valid JSON object matching this schema:
{{
  "question": "The interview question here",
  "context_snippet": "Brief note on why this question is relevant to the candidate's profile/role",
  "example_answer": "A concise outline of a high-scoring, thorough candidate answer"
}}
"""
        for model in [PRIMARY_MODEL] + FALLBACK_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a professional technical interviewer who returns strict JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=600,
                )
                raw_json = response.choices[0].message.content or "{}"
                parsed = json.loads(raw_json)
                question_text = parsed.get("question", "").strip()
                context_snippet = parsed.get("context_snippet", "").strip()
                example_answer = parsed.get("example_answer", "").strip()
                if question_text:
                    break
            except Exception as e:
                logger.warning("Groq question generation failed on model %s: %s", model, e)
                continue

    # Controlled fallback if LLM offline or empty response
    if not question_text:
        role_questions = FALLBACK_QUESTIONS.get(session.role_name, FALLBACK_QUESTIONS["Software Engineer"])
        cat_questions = role_questions.get(session.category, role_questions.get("technical", []))
        if cat_questions:
            q_idx = (turn_number - 1) % len(cat_questions)
            fallback_item = cat_questions[q_idx]
            question_text = fallback_item["question"]
            context_snippet = fallback_item.get("context", f"Core requirement for {session.role_name}")
            example_answer = "Provide a structured answer stating your approach, tradeoffs, and quantifiable impact."
        else:
            question_text = f"Can you explain your technical architecture approach when building systems for a {session.role_name} role?"
            context_snippet = f"Standard architectural evaluation for {session.role_name}"
            example_answer = "Outline system requirements, data flow, modular design, and failure modes."

    turn = InterviewTurn(
        session_id=session_id,
        turn_number=turn_number,
        question_text=question_text,
        question_type=session.category,
        context_snippet=context_snippet,
        example_answer=example_answer,
        created_at=datetime.utcnow(),
    )
    db.add(turn)
    db.commit()
    db.refresh(turn)

    return {
        "turn_id": turn.id,
        "turn_number": turn.turn_number,
        "question": turn.question_text,
        "category": turn.question_type,
        "context_snippet": turn.context_snippet,
    }


def evaluate_candidate_answer(
    turn_id: int,
    user_answer: str,
    db: Session,
) -> Dict[str, Any]:
    """Evaluate candidate answer using consistent 5-dimension rubric.

    Rubric:
    - Correctness (25%)
    - Completeness (20%)
    - Technical Depth (25%)
    - Clarity (15%)
    - Relevance (15%)
    """
    turn = db.query(InterviewTurn).filter(InterviewTurn.id == turn_id).first()
    if not turn:
        raise ValueError(f"Interview turn {turn_id} not found.")

    session = db.query(InterviewSession).filter(InterviewSession.id == turn.session_id).first()
    if not session:
        raise ValueError("Parent interview session not found.")

    client = _get_groq_client()
    rubric = {
        "correctness": 70.0,
        "completeness": 65.0,
        "technical_depth": 65.0,
        "clarity": 75.0,
        "relevance": 75.0,
    }
    feedback = ""
    missing_concepts: List[str] = []
    example_answer = turn.example_answer or ""

    if client and user_answer.strip():
        prompt = f"""You are an expert technical interviewer evaluating a candidate's answer for '{session.role_name}'.

Question Asked:
"{turn.question_text}"

Candidate Answer:
"{user_answer}"

Category: {turn.question_type}
Difficulty: {session.difficulty}

Evaluate against this 5-dimension rubric (each 0 to 100):
1. Correctness (25%)
2. Completeness (20%)
3. Technical Depth (25%)
4. Clarity (15%)
5. Relevance (15%)

Return ONLY a valid JSON object matching this schema:
{{
  "rubric": {{
    "correctness": 80,
    "completeness": 75,
    "technical_depth": 70,
    "clarity": 85,
    "relevance": 90
  }},
  "feedback": "2-3 sentences of constructive, actionable critique.",
  "missing_concepts": ["Specific technical term 1", "Specific tradeoff 2"],
  "improved_example": "A concise gold-standard answer demonstrating ideal depth."
}}
"""
        for model in [PRIMARY_MODEL] + FALLBACK_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a fair, rigorous technical interview evaluator returning strict JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=700,
                )
                raw_json = response.choices[0].message.content or "{}"
                data = json.loads(raw_json)
                if "rubric" in data and isinstance(data["rubric"], dict):
                    rubric = data["rubric"]
                    feedback = data.get("feedback", "")
                    missing_concepts = data.get("missing_concepts", [])
                    if data.get("improved_example"):
                        example_answer = data["improved_example"]
                    break
            except Exception as e:
                logger.warning("Groq evaluation failed on model %s: %s", model, e)
                continue

    # Fallback heuristic evaluation if LLM was unavailable
    if not feedback:
        word_count = len(user_answer.strip().split())
        if word_count < 15:
            score_base = 40.0
            feedback = "Answer is too brief. Provide structured context, specific technical tools, and implementation details."
            missing_concepts = ["Technical implementation detail", "Concrete examples", "Tradeoff analysis"]
        elif word_count < 40:
            score_base = 65.0
            feedback = "Good initial response. Expand further on architecture decisions, performance implications, and edge cases."
            missing_concepts = ["Performance metrics", "Alternative approaches considered"]
        else:
            score_base = 82.0
            feedback = "Strong, articulated answer with solid conceptual grounding. Good explanation of technical workflow."
            missing_concepts = ["Specific edge case handling"]

        rubric = {
            "correctness": score_base,
            "completeness": score_base - 5,
            "technical_depth": score_base,
            "clarity": score_base + 5,
            "relevance": score_base + 2,
        }

    # Calculate weighted total score
    total_score = round(
        0.25 * float(rubric.get("correctness", 70))
        + 0.20 * float(rubric.get("completeness", 65))
        + 0.25 * float(rubric.get("technical_depth", 65))
        + 0.15 * float(rubric.get("clarity", 75))
        + 0.15 * float(rubric.get("relevance", 75)),
        1
    )
    total_score = min(100.0, max(0.0, total_score))

    turn.user_answer = user_answer
    turn.score = total_score
    turn.evaluation_rubric = rubric
    turn.feedback = feedback
    turn.missing_concepts = missing_concepts
    turn.example_answer = example_answer
    turn.answered_at = datetime.utcnow()
    db.commit()

    return {
        "turn_id": turn.id,
        "score": total_score,
        "rubric": rubric,
        "feedback": feedback,
        "missing_concepts": missing_concepts,
        "example_answer": example_answer,
    }


def finish_interview_session(
    session_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Complete interview session and generate final performance scorecard."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError(f"Interview session {session_id} not found.")

    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_number)
        .all()
    )

    answered_turns = [t for t in turns if t.score is not None]

    if not answered_turns:
        session.status = "completed"
        session.overall_score = 0.0
        session.completed_at = datetime.utcnow()
        session.final_feedback = "No interview questions were answered."
        db.commit()
        return {
            "session_id": session.id,
            "role_name": session.role_name,
            "overall_score": 0.0,
            "turns_count": 0,
            "strengths": [],
            "improvements": ["Complete interview turns for a comprehensive assessment."],
            "final_feedback": session.final_feedback,
        }

    avg_score = round(sum(t.score for t in answered_turns) / len(answered_turns), 1)

    # Compile strengths & improvements
    strengths = []
    improvements = []
    all_missing: List[str] = []

    for t in answered_turns:
        if (t.score or 0) >= 75:
            strengths.append(f"Strong response on Question #{t.turn_number} ({t.question_type}).")
        else:
            improvements.append(f"Review core concepts from Question #{t.turn_number} ({t.question_type}).")

        if t.missing_concepts and isinstance(t.missing_concepts, list):
            all_missing.extend(t.missing_concepts)

    if avg_score >= 80:
        final_feedback = f"Outstanding performance for {session.role_name}. Candidate demonstrates high depth, clarity, and architectural maturity."
    elif avg_score >= 65:
        final_feedback = f"Good baseline readiness for {session.role_name}. Focus on strengthening depth in specific project defense answers and edge cases."
    else:
        final_feedback = f"Foundational preparation needed for {session.role_name}. Recommended practice: review missed technical concepts and practice STAR-format answers."

    unique_improvements = list(dict.fromkeys(improvements + all_missing[:4]))
    if not strengths:
        strengths.append("Willingness to practice and engage with rigorous interview scenarios.")

    session.status = "completed"
    session.overall_score = avg_score
    session.strengths = strengths[:5]
    session.improvements = unique_improvements[:5]
    session.final_feedback = final_feedback
    session.completed_at = datetime.utcnow()
    db.commit()

    return {
        "session_id": session.id,
        "role_name": session.role_name,
        "category": session.category,
        "overall_score": avg_score,
        "turns_count": len(answered_turns),
        "strengths": session.strengths,
        "improvements": session.improvements,
        "final_feedback": session.final_feedback,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "disclaimer": "AI mock interview feedback is an educational simulation and estimate, not a guarantee of real interview performance.",
    }


def get_interview_history(
    profile_id: UUID,
    db: Session,
    limit: int = 15,
    offset: int = 0,
) -> Dict[str, Any]:
    """Retrieve candidate's past interview sessions."""
    query = (
        db.query(InterviewSession)
        .filter(InterviewSession.profile_id == profile_id)
        .order_by(InterviewSession.created_at.desc())
    )

    total_count = query.count()
    sessions = query.offset(offset).limit(limit).all()

    return {
        "total_count": total_count,
        "sessions": [
            {
                "id": s.id,
                "role_name": s.role_name,
                "category": s.category,
                "difficulty": s.difficulty,
                "status": s.status,
                "overall_score": s.overall_score,
                "strengths": s.strengths,
                "improvements": s.improvements,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in sessions
        ],
    }

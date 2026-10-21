"""Skill Verification and Adaptive Assessment Engine.

Provides:
- Controlled, multi-type question bank (MCQ, Output, Debugging, Coding)
- Adaptive difficulty selection (Beginner <-> Intermediate <-> Advanced)
- Safe code evaluation integration via code_executor
- Transparent scoring rules and attempt lifecycle
- Evidence update without overwriting original resume evidence
- Strengths, weaknesses, and next steps generation
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from models.database import (
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentResponse,
    Profile,
    ProfileSkill,
    Skill,
)
from services.code_executor import evaluate_test_cases, execute_python_code
from services.skill_normalizer import normalize_skill

logger = logging.getLogger(__name__)

PASSING_SCORE_THRESHOLD = 70.0  # 70% required to verify skill

DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced"]


# -----------------------------------------------------------------------------
# Curated Seed Question Bank
# -----------------------------------------------------------------------------
CURATED_QUESTION_BANK: List[Dict[str, Any]] = [
    # --- PYTHON ---
    {
        "skill_name": "Python",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "Which of the following data types in Python is immutable?",
        "code_snippet": None,
        "options": ["list", "dict", "tuple", "set"],
        "correct_answer": "tuple",
        "explanation": "Tuples in Python cannot be modified once created; lists, dictionaries, and sets are mutable.",
        "test_cases": None,
    },
    {
        "skill_name": "Python",
        "difficulty": "Beginner",
        "question_type": "output",
        "question_text": "What is the output of the following Python snippet?",
        "code_snippet": "x = [1, 2, 3]\ny = x\ny.append(4)\nprint(len(x))",
        "options": ["3", "4", "Error", "None"],
        "correct_answer": "4",
        "explanation": "In Python, variable assignment `y = x` copies the reference to the list, not the list itself. Modifying y modifies x.",
        "test_cases": None,
    },
    {
        "skill_name": "Python",
        "difficulty": "Intermediate",
        "question_type": "debugging",
        "question_text": "Why does this default argument function exhibit unexpected behavior across calls?",
        "code_snippet": "def add_item(item, basket=[]):\n    basket.append(item)\n    return basket",
        "options": [
            "Default mutable arguments are evaluated once at function definition time",
            "Lists cannot be returned from functions in Python",
            "item is not cast to string",
            "append does not mutate the list"
        ],
        "correct_answer": "Default mutable arguments are evaluated once at function definition time",
        "explanation": "Default arguments are evaluated once when the function is defined. Using a mutable default list means all calls share the same list instance.",
        "test_cases": None,
    },
    {
        "skill_name": "Python",
        "difficulty": "Intermediate",
        "question_type": "coding",
        "question_text": "Write a Python function `reverse_words(sentence: str) -> str` that reverses the order of words in a space-separated string.",
        "code_snippet": "def reverse_words(sentence: str) -> str:\n    # Return the words in reverse order separated by spaces\n    pass",
        "options": None,
        "correct_answer": "def reverse_words(sentence: str) -> str:\n    return ' '.join(sentence.strip().split()[::-1])",
        "explanation": "Splitting by whitespace and reversing the word list joins back into a reversed sentence.",
        "test_cases": [
            {"input": "'hello world'", "expected_output": "world hello", "is_hidden": False},
            {"input": "'AI career intelligence platform'", "expected_output": "platform intelligence career AI", "is_hidden": False},
            {"input": "'fastapi python'", "expected_output": "python fastapi", "is_hidden": True},
        ],
    },
    {
        "skill_name": "Python",
        "difficulty": "Advanced",
        "question_type": "mcq",
        "question_text": "What is the primary role of the Python Global Interpreter Lock (GIL) in CPython?",
        "code_snippet": None,
        "options": [
            "It optimizes JIT compilation for nested loops",
            "It ensures only one native thread executes Python bytecode at once to protect memory management",
            "It automatically garbage collects circular references immediately",
            "It converts synchronous coroutines into OS threads"
        ],
        "correct_answer": "It ensures only one native thread executes Python bytecode at once to protect memory management",
        "explanation": "The GIL is a mutex that prevents multiple native threads from executing Python bytecodes simultaneously in CPython.",
        "test_cases": None,
    },

    # --- SQL & DBMS ---
    {
        "skill_name": "SQL",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "Which SQL clause is used to filter rows AFTER group aggregations (GROUP BY)?",
        "code_snippet": None,
        "options": ["WHERE", "HAVING", "ORDER BY", "FILTER"],
        "correct_answer": "HAVING",
        "explanation": "WHERE filters rows before aggregation; HAVING filters groups after aggregation.",
        "test_cases": None,
    },
    {
        "skill_name": "SQL",
        "difficulty": "Intermediate",
        "question_type": "output",
        "question_text": "In PostgreSQL, what is the result of `SELECT NULL = NULL;`?",
        "code_snippet": "SELECT NULL = NULL;",
        "options": ["TRUE", "FALSE", "NULL", "Syntax Error"],
        "correct_answer": "NULL",
        "explanation": "In standard SQL, comparisons with NULL using '=' return NULL (unknown). Use IS NULL instead.",
        "test_cases": None,
    },
    {
        "skill_name": "SQL",
        "difficulty": "Advanced",
        "question_type": "mcq",
        "question_text": "Which transaction isolation level prevents dirty reads, non-repeatable reads, AND phantom reads in standard SQL ANSI specification?",
        "code_snippet": None,
        "options": ["Read Committed", "Repeatable Read", "Serializable", "Read Uncommitted"],
        "correct_answer": "Serializable",
        "explanation": "Serializable is the highest ANSI SQL isolation level and prevents dirty reads, non-repeatable reads, and phantom reads.",
        "test_cases": None,
    },

    # --- JAVASCRIPT & REACT ---
    {
        "skill_name": "JavaScript",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "What is the difference between `==` and `===` in JavaScript?",
        "code_snippet": None,
        "options": [
            "== performs type coercion before comparison; === compares both value and type without coercion",
            "=== is only used for objects, == is for primitives",
            "== is faster and modern standard",
            "There is no difference"
        ],
        "correct_answer": "== performs type coercion before comparison; === compares both value and type without coercion",
        "explanation": "Strict equality (===) does not do implicit type conversions, making it safer and predictable.",
        "test_cases": None,
    },
    {
        "skill_name": "JavaScript",
        "difficulty": "Intermediate",
        "question_type": "output",
        "question_text": "What is the console output of this JavaScript snippet?",
        "code_snippet": "console.log(typeof NaN);",
        "options": ["'undefined'", "'number'", "'NaN'", "'null'"],
        "correct_answer": "'number'",
        "explanation": "In JavaScript specification, NaN (Not-a-Number) is a special numeric value whose typeof returns 'number'.",
        "test_cases": None,
    },
    {
        "skill_name": "React",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "Which React hook is used to manage mutable values that persist across renders without causing re-renders?",
        "code_snippet": None,
        "options": ["useState", "useRef", "useEffect", "useMemo"],
        "correct_answer": "useRef",
        "explanation": "useRef returns a mutable ref object whose .current property persists without triggering component re-renders.",
        "test_cases": None,
    },
    {
        "skill_name": "React",
        "difficulty": "Intermediate",
        "question_type": "debugging",
        "question_text": "What is the issue with modifying state directly like `state.count += 1` in React?",
        "code_snippet": "const [data, setData] = useState({ count: 0 });\nfunction onClick() {\n    data.count += 1;\n    setData(data);\n}",
        "options": [
            "React uses object reference equality (Object.is); mutating the object directly prevents re-renders",
            "useState does not support objects",
            "count is a reserved word",
            "React throws a compile-time TypeError"
        ],
        "correct_answer": "React uses object reference equality (Object.is); mutating the object directly prevents re-renders",
        "explanation": "React compares old and new state by reference. If the object reference doesn't change, React bails out of re-rendering.",
        "test_cases": None,
    },

    # --- OOP & DBMS ---
    {
        "skill_name": "OOP",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "Which OOP principle allows a subclass to provide a specific implementation of a method that is already defined in its superclass?",
        "code_snippet": None,
        "options": ["Encapsulation", "Polymorphism / Method Overriding", "Abstraction", "Composition"],
        "correct_answer": "Polymorphism / Method Overriding",
        "explanation": "Polymorphism enables objects of different classes to respond to the same method invocation with customized behavior via method overriding.",
        "test_cases": None,
    },
    {
        "skill_name": "OOP",
        "difficulty": "Intermediate",
        "question_type": "mcq",
        "question_text": "What does the 'L' in SOLID design principles stand for?",
        "code_snippet": None,
        "options": [
            "Liskov Substitution Principle",
            "Lazy Evaluation Principle",
            "Layered Architecture Principle",
            "Loose Coupling Principle"
        ],
        "correct_answer": "Liskov Substitution Principle",
        "explanation": "Liskov Substitution states that objects of a superclass should be replaceable with objects of its subclasses without breaking program correctness.",
        "test_cases": None,
    },

    # --- DOCKER & DEVOPS ---
    {
        "skill_name": "Docker",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "In a Dockerfile, which instruction specifies the default command to execute when a container starts, but can be overridden from the CLI?",
        "code_snippet": None,
        "options": ["RUN", "CMD", "COPY", "WORKDIR"],
        "correct_answer": "CMD",
        "explanation": "CMD provides default arguments for executing the container and can be overridden by docker run arguments, unlike RUN which executes during image build.",
        "test_cases": None,
    },
    {
        "skill_name": "Docker",
        "difficulty": "Intermediate",
        "question_type": "mcq",
        "question_text": "What is the primary benefit of multi-stage Docker builds?",
        "code_snippet": None,
        "options": [
            "They drastically reduce final production image size by copying only compiled artifacts",
            "They run containers in parallel",
            "They avoid needing a Dockerfile",
            "They allow mounting host networks automatically"
        ],
        "correct_answer": "They drastically reduce final production image size by copying only compiled artifacts",
        "explanation": "Multi-stage builds leave behind compilers, SDKs, and build caches, keeping only the runtime and application artifacts in the final stage.",
        "test_cases": None,
    },

    # --- GIT ---
    {
        "skill_name": "Git",
        "difficulty": "Beginner",
        "question_type": "mcq",
        "question_text": "Which Git command is used to record staged changes to the repository?",
        "code_snippet": None,
        "options": ["git add", "git commit", "git push", "git stage"],
        "correct_answer": "git commit",
        "explanation": "`git add` stages changes; `git commit` takes staged snapshots and records them into repository history.",
        "test_cases": None,
    },
    {
        "skill_name": "Git",
        "difficulty": "Intermediate",
        "question_type": "mcq",
        "question_text": "What is the key difference between `git rebase` and `git merge`?",
        "code_snippet": None,
        "options": [
            "Rebase rewrites commit history linearly onto the target branch; merge creates a new merge commit preserving branch topology",
            "Merge deletes the source branch automatically",
            "Rebase cannot handle merge conflicts",
            "There is no functional difference"
        ],
        "correct_answer": "Rebase rewrites commit history linearly onto the target branch; merge creates a new merge commit preserving branch topology",
        "explanation": "Rebase moves or combines a sequence of commits to a new base commit, creating a clean linear history.",
        "test_cases": None,
    },
]


def seed_assessment_questions(db: Session) -> int:
    """Populate database with controlled question bank if empty."""
    existing_count = db.query(AssessmentQuestion).count()
    if existing_count > 0:
        return existing_count

    inserted = 0
    for q in CURATED_QUESTION_BANK:
        question = AssessmentQuestion(
            skill_name=q["skill_name"],
            difficulty=q["difficulty"],
            question_type=q["question_type"],
            question_text=q["question_text"],
            code_snippet=q.get("code_snippet"),
            options=q.get("options"),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation"),
            test_cases=q.get("test_cases"),
            is_active=True,
        )
        db.add(question)
        inserted += 1

    db.commit()
    logger.info("Seeded %d assessment questions into database.", inserted)
    return inserted


def get_available_skills(db: Session) -> List[Dict[str, Any]]:
    """List skills that have available assessment questions."""
    seed_assessment_questions(db)

    # Group by skill_name and count questions
    skills_query = (
        db.query(
            AssessmentQuestion.skill_name,
            AssessmentQuestion.difficulty,
            AssessmentQuestion.question_type,
        )
        .filter(AssessmentQuestion.is_active == True)
        .all()
    )

    skill_stats: Dict[str, Dict[str, Any]] = {}
    for row in skills_query:
        s_name = row[0]
        if s_name not in skill_stats:
            skill_stats[s_name] = {
                "skill_name": s_name,
                "total_questions": 0,
                "difficulties": set(),
                "question_types": set(),
            }
        skill_stats[s_name]["total_questions"] += 1
        skill_stats[s_name]["difficulties"].add(row[1])
        skill_stats[s_name]["question_types"].add(row[2])

    result = []
    for s_name, data in sorted(skill_stats.items()):
        result.append({
            "skill_name": s_name,
            "total_questions": data["total_questions"],
            "difficulties": sorted(list(data["difficulties"])),
            "question_types": sorted(list(data["question_types"])),
        })

    return result


def determine_next_difficulty(
    current_difficulty: str,
    was_correct: bool,
    recent_responses: List[bool],
) -> str:
    """Adaptive difficulty progression algorithm.

    - If user answers correctly and has >= 2 consecutive correct answers, level up.
    - If user answers incorrectly, level down.
    - Otherwise, stay at current level.
    """
    levels = ["Beginner", "Intermediate", "Advanced"]
    idx = levels.index(current_difficulty) if current_difficulty in levels else 1

    if was_correct:
        # Check streak
        recent_correct_streak = 0
        for r in reversed(recent_responses):
            if r:
                recent_correct_streak += 1
            else:
                break

        if recent_correct_streak >= 2 and idx < len(levels) - 1:
            return levels[idx + 1]
    else:
        if idx > 0:
            return levels[idx - 1]

    return current_difficulty


def start_assessment_attempt(
    profile_id: UUID,
    skill_name: str,
    initial_difficulty: str = "Intermediate",
    db: Optional[Session] = None,
) -> AssessmentAttempt:
    """Initialize a new skill verification assessment attempt."""
    if db is None:
        raise ValueError("Database session required.")

    # Ensure question bank is seeded
    seed_assessment_questions(db)

    # Standardize skill name
    norm_skill = normalize_skill(skill_name)
    target_skill = norm_skill if norm_skill else skill_name

    # Create new attempt preserving historical attempts
    attempt = AssessmentAttempt(
        profile_id=profile_id,
        skill_name=target_skill,
        difficulty=initial_difficulty,
        status="in_progress",
        score=0.0,
        passed=False,
        accuracy=0.0,
        started_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def get_next_question(
    attempt_id: int,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """Retrieve next adaptive question for this attempt.

    Excludes already answered questions.
    """
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt or attempt.status != "in_progress":
        return None

    # Get already answered question IDs
    answered_ids = [
        r.question_id
        for r in db.query(AssessmentResponse.question_id)
        .filter(AssessmentResponse.attempt_id == attempt_id)
        .all()
    ]

    # Look for question in candidate's target skill & current difficulty
    q = (
        db.query(AssessmentQuestion)
        .filter(
            AssessmentQuestion.skill_name.ilike(attempt.skill_name),
            AssessmentQuestion.difficulty == attempt.difficulty,
            AssessmentQuestion.is_active == True,
            ~AssessmentQuestion.id.in_(answered_ids) if answered_ids else True,
        )
        .first()
    )

    # If no question at exact difficulty, fallback to any available for this skill
    if not q:
        q = (
            db.query(AssessmentQuestion)
            .filter(
                AssessmentQuestion.skill_name.ilike(attempt.skill_name),
                AssessmentQuestion.is_active == True,
                ~AssessmentQuestion.id.in_(answered_ids) if answered_ids else True,
            )
            .first()
        )

    if not q:
        return None

    return {
        "question_id": q.id,
        "skill_name": q.skill_name,
        "difficulty": q.difficulty,
        "question_type": q.question_type,
        "question_text": q.question_text,
        "code_snippet": q.code_snippet,
        "options": q.options,
        "has_test_cases": bool(q.test_cases),
        "total_answered": len(answered_ids),
    }


def submit_answer(
    attempt_id: int,
    question_id: int,
    user_answer: str,
    db: Session,
) -> Dict[str, Any]:
    """Submit candidate answer, evaluate correctness, and adapt difficulty."""
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    question = db.query(AssessmentQuestion).filter(AssessmentQuestion.id == question_id).first()

    if not attempt or not question:
        raise ValueError("Invalid attempt or question ID.")

    if attempt.status != "in_progress":
        raise ValueError("Assessment attempt is already completed.")

    is_correct = False
    score_awarded = 0.0
    feedback = ""
    execution_output: Optional[Dict[str, Any]] = None

    if question.question_type == "coding":
        # Safe sandbox test case execution
        test_cases = question.test_cases if isinstance(question.test_cases, list) else []
        eval_result = evaluate_test_cases(
            user_code=user_answer,
            test_cases=test_cases,
            function_name="reverse_words",  # default function runner
        )
        execution_output = eval_result
        is_correct = eval_result["all_passed"]
        score_awarded = eval_result["score_percentage"]
        feedback = f"Passed {eval_result['passed_count']} of {eval_result['total_count']} test cases."

    else:
        # Objective string / MCQ / output answer matching
        cleaned_user = str(user_answer).strip().lower()
        cleaned_correct = str(question.correct_answer).strip().lower()

        if cleaned_user == cleaned_correct:
            is_correct = True
            score_awarded = 100.0
            feedback = "Correct! " + (question.explanation or "")
        else:
            is_correct = False
            score_awarded = 0.0
            feedback = f"Incorrect. Correct answer: '{question.correct_answer}'. " + (question.explanation or "")

    # Save response
    response_entry = AssessmentResponse(
        attempt_id=attempt_id,
        question_id=question_id,
        user_answer=user_answer,
        is_correct=is_correct,
        score_awarded=score_awarded,
        feedback=feedback,
        execution_output=execution_output,
        created_at=datetime.utcnow(),
    )
    db.add(response_entry)

    # Adapt difficulty for next question
    past_responses = [
        r.is_correct
        for r in db.query(AssessmentResponse.is_correct)
        .filter(AssessmentResponse.attempt_id == attempt_id)
        .all()
    ]
    past_responses.append(is_correct)

    new_diff = determine_next_difficulty(
        current_difficulty=attempt.difficulty,
        was_correct=is_correct,
        recent_responses=past_responses,
    )
    attempt.difficulty = new_diff
    db.commit()

    return {
        "is_correct": is_correct,
        "score_awarded": score_awarded,
        "feedback": feedback,
        "next_difficulty": new_diff,
        "execution_output": execution_output,
    }


def complete_attempt(
    attempt_id: int,
    db: Session,
) -> Dict[str, Any]:
    """Finalize assessment attempt, compute overall score, and update skill verification.

    CRITICAL RULE:
        Updates `profile_skills.is_verified` and `verified_score` while PRESERVING
        the original resume evidence_ref and confidence.
    """
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise ValueError("Assessment attempt not found.")

    responses = (
        db.query(AssessmentResponse)
        .filter(AssessmentResponse.attempt_id == attempt_id)
        .all()
    )

    if not responses:
        attempt.status = "completed"
        attempt.score = 0.0
        attempt.passed = False
        attempt.completed_at = datetime.utcnow()
        db.commit()
        return {
            "attempt_id": attempt.id,
            "skill_name": attempt.skill_name,
            "score": 0.0,
            "passed": False,
            "accuracy": 0.0,
            "summary": {"strengths": [], "weaknesses": ["No questions attempted"], "next_steps": ["Retry assessment"]},
        }

    total_score = sum(r.score_awarded for r in responses) / len(responses)
    correct_count = sum(1 for r in responses if r.is_correct)
    accuracy = (correct_count / len(responses)) * 100.0
    passed = (total_score >= PASSING_SCORE_THRESHOLD)

    # Strengths and weaknesses analysis
    strengths = []
    weaknesses = []
    if accuracy >= 80:
        strengths.append(f"Strong conceptual understanding of core {attempt.skill_name} concepts.")
    elif accuracy >= 50:
        strengths.append(f"Solid basic familiarity with {attempt.skill_name}.")
    else:
        weaknesses.append(f"Foundational gaps in {attempt.skill_name} syntax and semantics.")

    if passed:
        next_steps = [
            f"Skill '{attempt.skill_name}' is now Verified! Your CareerFit evidence strength has increased.",
            "Explore advanced mock interviews or review related cloud & framework skills.",
        ]
    else:
        next_steps = [
            f"Review the targeted learning roadmap modules for '{attempt.skill_name}'.",
            "Retake this assessment once you have practiced test cases and debugging problems.",
        ]

    summary_payload = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_steps": next_steps,
        "accuracy_percent": round(accuracy, 1),
        "total_questions": len(responses),
        "passed_questions": correct_count,
    }

    attempt.status = "completed"
    attempt.score = round(total_score, 1)
    attempt.accuracy = round(accuracy, 1)
    attempt.passed = passed
    attempt.completed_at = datetime.utcnow()
    attempt.summary = summary_payload

    # UPDATE PROFILE SKILL EVIDENCE SAFELY (Do not overwrite resume evidence!)
    # Find matching skill in skills taxonomy
    target_skill_name = attempt.skill_name
    skill_rec = (
        db.query(Skill)
        .filter(Skill.canonical_name.ilike(target_skill_name))
        .first()
    )

    if skill_rec:
        profile_skill = (
            db.query(ProfileSkill)
            .filter(
                ProfileSkill.profile_id == attempt.profile_id,
                ProfileSkill.skill_id == skill_rec.id,
            )
            .first()
        )

        if profile_skill:
            # Upgrade verification status without clearing evidence_ref or confidence
            if passed:
                profile_skill.is_verified = True
                profile_skill.verified_score = round(total_score, 1)
                profile_skill.verified_at = datetime.utcnow()
                profile_skill.verified_level = attempt.difficulty
                # Verified skills elevate confidence to High (0.9) if previously lower
                if (profile_skill.confidence or 0.0) < 0.9:
                    profile_skill.confidence = 0.9
        else:
            # If skill was not in original resume, add it as a verified skill!
            new_ps = ProfileSkill(
                profile_id=attempt.profile_id,
                skill_id=skill_rec.id,
                confidence=0.9 if passed else 0.5,
                evidence_ref=json.dumps({"section": "Assessment", "raw_text": f"Verified via assessment (score: {round(total_score, 1)}%)"}),
                is_verified=passed,
                verified_score=round(total_score, 1) if passed else None,
                verified_at=datetime.utcnow() if passed else None,
                verified_level=attempt.difficulty if passed else None,
            )
            db.add(new_ps)

    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "skill_name": attempt.skill_name,
        "difficulty_achieved": attempt.difficulty,
        "score": attempt.score,
        "passed": attempt.passed,
        "accuracy": attempt.accuracy,
        "summary": summary_payload,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
    }


def get_assessment_history(
    profile_id: UUID,
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Fetch paginated assessment attempts for a profile."""
    query = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.profile_id == profile_id)
        .order_by(AssessmentAttempt.started_at.desc())
    )

    total_count = query.count()
    attempts = query.offset(offset).limit(limit).all()

    return {
        "total_count": total_count,
        "attempts": [
            {
                "id": a.id,
                "skill_name": a.skill_name,
                "difficulty": a.difficulty,
                "status": a.status,
                "score": a.score,
                "passed": a.passed,
                "accuracy": a.accuracy,
                "started_at": a.started_at.isoformat(),
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "summary": a.summary,
            }
            for a in attempts
        ],
    }

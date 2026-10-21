# AI-Based Career Intelligence and Skill Analysis Platform

A full-stack, enterprise-grade career intelligence platform that combines deterministic scoring engines, automated skill extraction, adaptive testing, opportunity matching, and AI-powered interview coaching.

---

## Table of Contents
1. [Platform Overview](#platform-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture & System Design](#architecture--system-design)
4. [New Features & Upgrades](#new-features--upgrades)
   - [1. Skill Verification & Adaptive Assessment Engine](#1-skill-verification--adaptive-assessment-engine)
   - [2. Job & Internship Matching Engine](#2-job--internship-matching-engine)
   - [3. AI Mock Interview Coach](#3-ai-mock-interview-coach)
5. [Deterministic Scoring Integrity](#deterministic-scoring-integrity)
6. [Security & Isolated Code Execution](#security--isolated-code-execution)
7. [Environment Configuration](#environment-configuration)
8. [Database & Migrations](#database--migrations)
9. [Running the Application](#running-the-application)
10. [Automated Test Suite](#automated-test-suite)
11. [API Reference](#api-reference)

---

## Platform Overview

The platform empowers job seekers and professionals to analyze resumes, benchmark skills against industry roles, verify proficiencies through adaptive assessments, discover tailored job opportunities, and practice role-specific technical and behavioral interviews.

### Core Invariants:
- **Deterministic Single Source of Truth**: All career-fit scores, readiness indexes, skill gap analyses, and matching metrics are computed deterministically using versioned mathematical models.
- **Explainability**: Generative AI (Groq Llama 3) provides natural language commentary and feedback, but **never invents or silently alters deterministic calculations**.
- **Separation of Resume Evidence & Verified Evidence**: Resume-claimed skills and assessment-verified competencies coexist without overwriting historical parsed data.

---

## Technology Stack

### Frontend
- **Framework**: Next.js 14 App Router (React 18, TypeScript)
- **Styling**: Tailwind CSS & Lucide React icons
- **State & Data Fetching**: React Hooks, Fetch API with JWT Bearer authentication
- **Speech API**: Web Speech API (`webkitSpeechRecognition`) for hands-free mock interview dictation

### Backend
- **Framework**: FastAPI (Python 3.10+) with Uvicorn
- **Validation**: Pydantic v2
- **ORM & Database**: SQLAlchemy 2.0 with PostgreSQL and Alembic migrations
- **Resume Parsing**: PyMuPDF (`fitz`), `python-docx`
- **NLP & Data Science**: spaCy, scikit-learn, Pandas, NumPy, Regex
- **AI / LLM Integration**: Groq API (`llama-3.3-70b-versatile` / `llama3-70b-8192`) with graceful offline fallback
- **Auth**: JWT (JSON Web Tokens) with Passlib / bcrypt password hashing
- **Code Execution Sandbox**: Python AST syntax tree security scanning and isolated child-process execution

---

## Architecture & System Design

```
├── backend/
│   ├── api/                     # FastAPI endpoint routers
│   │   ├── auth.py              # User authentication & registration
│   │   ├── resume.py            # PDF/DOCX parsing & skill extraction
│   │   ├── careers.py           # Career-fit scoring & target role selection
│   │   ├── gaps.py              # Skill-gap & readiness calculation
│   │   ├── simulate.py          # What-if career simulator
│   │   ├── ats.py               # ATS resume optimization checker
│   │   ├── market.py            # Market demand, salary benchmarks & trends
│   │   ├── roadmaps.py          # AI personalized learning roadmaps
│   │   ├── progress.py          # Learning milestone tracker
│   │   ├── progression.py       # Career path ladder & milestone progression
│   │   ├── assessments.py       # [NEW] Adaptive testing & code verification
│   │   ├── jobs.py              # [NEW] Job matching & application tracker
│   │   └── interviews.py        # [NEW] AI mock interview sessions & rubrics
│   ├── models/
│   │   └── database.py          # SQLAlchemy 2.0 database schemas
│   ├── scoring/                 # Deterministic scoring engines
│   │   ├── career_scorer.py     # CareerFit formula implementation
│   │   ├── gap_engine.py        # Skill gap analysis & readiness engine
│   │   ├── ats_scorer.py        # ATS parsing & keyword matching
│   │   └── salary_analyzer.py   # Salary percentiles & benchmarks
│   ├── services/
│   │   ├── code_executor.py     # [NEW] Sandboxed Python code executor with AST scan
│   │   ├── assessment_engine.py # [NEW] Question bank & adaptive difficulty controller
│   │   ├── job_matcher.py       # [NEW] Opportunity matcher & URL deduplication
│   │   ├── interview_coach.py   # [NEW] Interview question generator & rubric evaluator
│   │   ├── groq_client.py       # Groq client wrapper
│   │   └── parser.py            # PyMuPDF and python-docx text extractor
│   └── tests/                   # Pytest automated test suite
├── frontend/
│   ├── app/
│   │   ├── assessments/         # Assessment catalog & interactive runner
│   │   ├── jobs/                # Job matching & Kanban application tracker
│   │   ├── interview/           # Mock interview coach & post-session review
│   │   ├── dashboard/           # Comprehensive candidate intelligence dashboard
│   │   ├── gaps/                # Skill gap visualizer
│   │   ├── roadmap/             # Personalized learning roadmap
│   │   ├── simulate/            # What-if career simulator
│   │   ├── ats/                 # ATS resume score & keyword analyzer
│   │   ├── progress/            # Skill progression tracking
│   │   ├── login/ & register/   # Authentication pages
│   ├── components/              # Shared UI components (Navbar, ScoreBar, etc.)
│   └── lib/api.ts               # Type-safe API client
```

---

## New Features & Upgrades

### 1. Skill Verification & Adaptive Assessment Engine
- **Question Types**: Multiple Choice Questions (MCQ), Output Prediction, Debugging snippets, and Python Coding challenges.
- **Adaptive Difficulty**: Questions dynamically adjust between Beginner, Intermediate, and Advanced based on the candidate's running accuracy.
- **Sandboxed Execution**: Python coding assessments run in disposable child-processes with timeouts, sanitized environments, and pre-execution AST syntax checks.
- **Evidence Dual-Tracking**: Resumes claim skills; assessments verify them. High scores (≥70%) set `is_verified=True` and log `verified_score` on `profile_skills` without overwriting the original resume source text.
- **Career-Fit Integration**: Verified skills award an evidence strength boost (e.g., +25% confidence per verified skill) in the deterministic `CareerFit` calculation.

### 2. Job & Internship Matching Engine
- **Transparent Formula**:
  $$\text{MatchScore} = 0.50 \times \text{SkillOverlap} + 0.20 \times \text{VerifiedSkillBonus} + 0.15 \times \text{ExperienceMatch} + 0.15 \times \text{LocationPref}$$
- **Data Ingestion & Deduplication**: Canonicalizes URLs (stripping query/UTM parameters) to guarantee zero duplicate listings across imports, manual entries, or seed datasets.
- **Pipeline Lifecycle**: Tracks full application lifecycle: `saved`, `applied`, `assessment`, `interview`, `offer`, and `rejected` with custom candidate notes.
- **Explainability**: Every matched opportunity displays matched skills, verified skills, missing skills, and clear reasons for match calculation.

### 3. AI Mock Interview Coach
- **Category Support**: Technical, Coding/Algorithm, Project-Defense, Resume-Walkthrough, and Behavioral/HR.
- **Resume-Grounded Questions**: Extracts actual project names and tech stacks from the candidate's resume to generate realistic project-defense questions.
- **Structured 5-Dimension Rubric**:
  - Correctness (0–100)
  - Completeness (0–100)
  - Technical Depth (0–100)
  - Clarity & Communication (0–100)
  - Relevance (0–100)
- **High-Fidelity Feedback**: Evaluates answers with constructive critique, identified missing concepts, a gold-standard model response, and recommended revision topics.
- **Offline Fallback Engine**: If the Groq API key is omitted or rate-limited, the system falls back to a curated role-specific question and evaluation bank without crashing.

---

## Deterministic Scoring Integrity

The system enforces a mathematical scoring standard:

$$\text{CareerFit} = 0.45 \times \text{SkillMatch} + 0.20 \times \text{EvidenceStrength} + 0.15 \times \text{ExperienceAlignment} + 0.10 \times \text{EducationAlignment} + 0.10 \times \text{MarketDemand}$$

When a candidate verifies a skill through the assessment engine:
1. `EvidenceStrength` is elevated because the claim is validated by code execution or question responses.
2. The skill gap analyzer marks the skill as `verified`, lowering priority for redundant remediation in roadmaps.
3. The job matcher awards a `VerifiedSkillBonus` for verified required competencies.

---

## Security & Isolated Code Execution

Arbitrary user code is **never** executed inside the main FastAPI application thread or process:
1. **AST Security Analysis**: Prior to execution, Python's Abstract Syntax Tree parser inspects the code. Any reference to blocked modules (`os`, `sys`, `subprocess`, `socket`, `shutil`, `urllib`, `requests`, `builtins`, `__import__`, `eval`, `exec`) is rejected with a 400 security error.
2. **Sanitized Environment**: Code executes via `subprocess.run` inside an isolated temporary directory with `DATABASE_URL`, `SECRET_KEY`, and API tokens stripped from `os.environ`.
3. **Execution Limits**: Hard 5.0-second execution timeout prevents infinite loops and denial-of-service attempts.

---

## Environment Configuration

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/career_intelligence
SECRET_KEY=your-jwt-secret-key-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GROQ_API_KEY=your_groq_api_key_here  # Optional; system uses graceful offline fallback if absent
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Database & Migrations

The database uses Alembic to manage migrations cleanly without data loss.

To apply migrations to your PostgreSQL database:
```bash
cd backend
..\venv\Scripts\alembic upgrade head
```

The database includes:
- `users`, `profiles`, `profile_skills`, `career_goals`
- `assessment_questions`, `assessment_attempts`, `assessment_responses`
- `job_opportunities`, `user_opportunities`
- `interview_sessions`, `interview_turns`

---

## Running the Application

### 1. Start Backend API
```bash
cd backend
..\venv\Scripts\uvicorn main:app --reload --port 8000
```
Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### 2. Start Frontend
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Automated Test Suite

Run the full pytest suite from the `backend/` directory:
```bash
cd backend
..\venv\Scripts\pytest -v
```

### Current Test Results:
```
tests/test_assessments.py::test_code_executor_safe_execution PASSED
tests/test_assessments.py::test_code_executor_timeout PASSED
tests/test_assessments.py::test_code_executor_security_violation PASSED
tests/test_assessments.py::test_evaluate_test_cases PASSED
tests/test_assessments.py::test_adaptive_difficulty_progression PASSED
tests/test_career_path.py::test_career_paths_completeness PASSED
tests/test_career_path.py::test_level_info_compatibility PASSED
tests/test_career_path.py::test_get_current_level_junior PASSED
tests/test_career_path.py::test_get_current_level_mid PASSED
tests/test_career_path.py::test_get_current_level_senior PASSED
tests/test_career_path.py::test_get_current_level_lead PASSED
tests/test_career_path.py::test_get_current_level_partial_match PASSED
tests/test_career_path.py::test_get_current_level_normalization_and_aliases PASSED
tests/test_interview_coach.py::test_interview_fallback_questions_available PASSED
tests/test_job_matcher.py::test_normalize_opportunity_url PASSED
tests/test_job_matcher.py::test_calculate_opportunity_match_with_verified_skills PASSED
tests/test_salary_analyzer.py::test_analyze_salary_with_synthetic_data PASSED
tests/test_salary_analyzer.py::test_analyze_salary_unknown_role PASSED
tests/test_salary_analyzer.py::test_analyze_salary_case_insensitivity PASSED
tests/test_salary_analyzer.py::test_get_all_roles_summary PASSED

20 passed in 5.67s (100% Pass Rate)
```

---

## API Reference

### Skill Verification & Assessments (`/api/assessments`)
- `GET /api/assessments/skills` — List available assessment skills & question counts
- `POST /api/assessments/attempts/start` — Start a new adaptive assessment attempt
- `GET /api/assessments/attempts/{attempt_id}/next` — Get the next adaptive question (answers hidden)
- `POST /api/assessments/attempts/{attempt_id}/submit` — Submit question answer or code; receives execution feedback
- `POST /api/assessments/attempts/{attempt_id}/complete` — Complete attempt; computes final score & updates verified skills
- `GET /api/assessments/attempts/{attempt_id}` — View complete attempt review with question breakdowns
- `GET /api/assessments/history` — Get user's full assessment attempt history

### Job & Opportunity Matching (`/api/jobs`)
- `GET /api/jobs/matches` — Get ranked opportunities with transparent matching scores & filter options
- `GET /api/jobs/pipeline` — Get tracked applications organized by status
- `POST /api/jobs/track` — Save or update application status (`saved`, `applied`, `interview`, etc.)
- `DELETE /api/jobs/track/{user_opp_id}` — Untrack an opportunity
- `POST /api/jobs/seed` — Ingest curated industry job listings
- `POST /api/jobs/manual` — Add a custom job opportunity with URL deduplication

### AI Mock Interview Coach (`/api/interviews`)
- `POST /api/interviews/sessions/start` — Initiate a personalized mock interview session
- `GET /api/interviews/sessions/{session_id}/next-question` — Retrieve the current interview question
- `POST /api/interviews/sessions/{session_id}/answer` — Submit answer; evaluate against 5-dimension rubric
- `POST /api/interviews/sessions/{session_id}/complete` — Finalize session and generate strengths/weaknesses report
- `GET /api/interviews/sessions/{session_id}` — View complete session evaluation
- `GET /api/interviews/history` — Retrieve all past interview sessions

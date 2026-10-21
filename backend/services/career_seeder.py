"""Career roles and skills taxonomy database seeder.

Defines canonical career profiles with descriptions and required skill lists,
and populates the database with skill taxonomy, career roles, and career skills.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import CareerRole, CareerSkill, Skill
from models.session import SessionLocal
from services.skill_extractor import SKILL_PATTERNS
from services.skill_normalizer import normalize_skill

# CAREER_PROFILES defining 10 canonical roles with required skills and descriptions
CAREER_PROFILES: Dict[str, Dict[str, Union[str, List[str]]]] = {
    "Software Engineer": {
        "description": "Designs, develops, and maintains software applications and systems using modern programming languages and development workflows.",
        "required_skills": [
            "Python",
            "Java",
            "JS",
            "SQL",
            "Git",
            "Docker",
            "REST APIs",
        ],
    },
    "Data Scientist": {
        "description": "Analyzes complex data to extract actionable insights, builds predictive models, and applies statistical methods.",
        "required_skills": [
            "Python",
            "SQL",
            "ML",
            "TensorFlow",
            "Pandas",
            "Statistics",
        ],
    },
    "Machine Learning Engineer": {
        "description": "Designs, trains, deploys, and monitors scalable machine learning models and production MLOps pipelines.",
        "required_skills": [
            "Python",
            "TensorFlow",
            "PyTorch",
            "Docker",
            "MLOps",
        ],
    },
    "Backend Developer": {
        "description": "Architects and implements server-side logic, database interactions, microservices, and RESTful APIs.",
        "required_skills": [
            "Python",
            "Node.js",
            "SQL",
            "REST APIs",
            "Docker",
            "Redis",
        ],
    },
    "Frontend Developer": {
        "description": "Builds responsive, performant, and accessible user interfaces and web applications using modern web technologies.",
        "required_skills": [
            "React",
            "JavaScript",
            "HTML",
            "CSS",
            "TypeScript",
            "Next.js",
        ],
    },
    "Full Stack Developer": {
        "description": "Develops end-to-end web applications combining interactive frontend interfaces with robust backend architectures.",
        "required_skills": [
            "React",
            "Node.js",
            "Python",
            "SQL",
            "Docker",
            "REST APIs",
        ],
    },
    "DevOps Engineer": {
        "description": "Automates software delivery, builds CI/CD pipelines, and manages reliable cloud infrastructure and orchestration.",
        "required_skills": [
            "Docker",
            "Kubernetes",
            "AWS",
            "CI/CD",
            "Linux",
            "Terraform",
        ],
    },
    "Data Analyst": {
        "description": "Collects, cleans, analyzes, and visualizes data to help organizations make informed business decisions.",
        "required_skills": [
            "SQL",
            "Python",
            "Pandas",
            "Excel",
            "Power BI",
            "Tableau",
        ],
    },
    "AI Engineer": {
        "description": "Builds and integrates artificial intelligence solutions, large language model applications, and intelligent systems.",
        "required_skills": [
            "Python",
            "LLM",
            "OpenCV",
            "NLP",
            "TensorFlow",
            "FastAPI",
        ],
    },
    "Cloud Engineer": {
        "description": "Designs, builds, and maintains scalable, secure, and resilient multi-cloud architectures and distributed services.",
        "required_skills": [
            "AWS",
            "Azure",
            "GCP",
            "Docker",
            "Kubernetes",
            "Terraform",
        ],
    },
}

# Domain categorization mapping for skills
_SKILL_CATEGORIES: Dict[str, str] = {
    # Programming Languages
    "Python": "Programming Languages",
    "Java": "Programming Languages",
    "JavaScript": "Programming Languages",
    "TypeScript": "Programming Languages",
    "Go": "Programming Languages",
    "Rust": "Programming Languages",
    "C": "Programming Languages",
    "C++": "Programming Languages",
    "C#": "Programming Languages",
    "Kotlin": "Programming Languages",
    "Swift": "Programming Languages",
    "Ruby": "Programming Languages",
    "PHP": "Programming Languages",
    "Scala": "Programming Languages",
    "R": "Programming Languages",
    "MATLAB": "Programming Languages",
    "Dart": "Programming Languages",
    "Bash": "Programming Languages",
    "SQL": "Programming Languages",
    # Frontend
    "React": "Frontend",
    "Vue.js": "Frontend",
    "Angular": "Frontend",
    "Svelte": "Frontend",
    "Next.js": "Frontend",
    "HTML": "Frontend",
    "CSS": "Frontend",
    "Sass": "Frontend",
    "Tailwind": "Frontend",
    "Bootstrap": "Frontend",
    "Redux": "Frontend",
    # Backend & APIs
    "Node.js": "Backend & APIs",
    "Express.js": "Backend & APIs",
    "FastAPI": "Backend & APIs",
    "Flask": "Backend & APIs",
    "Django": "Backend & APIs",
    "Spring Boot": "Backend & APIs",
    "GraphQL": "Backend & APIs",
    "gRPC": "Backend & APIs",
    "REST APIs": "Backend & APIs",
    "Prisma": "Backend & APIs",
    # Databases & Messaging
    "PostgreSQL": "Databases",
    "MySQL": "Databases",
    "MongoDB": "Databases",
    "Redis": "Databases",
    "Elasticsearch": "Databases",
    "SQLite": "Databases",
    "Snowflake": "Databases",
    "Kafka": "Databases",
    "RabbitMQ": "Databases",
    # AI / ML & Data Science
    "Machine Learning": "Machine Learning & AI",
    "Deep Learning": "Machine Learning & AI",
    "NLP": "Machine Learning & AI",
    "Computer Vision": "Machine Learning & AI",
    "TensorFlow": "Machine Learning & AI",
    "PyTorch": "Machine Learning & AI",
    "Scikit-learn": "Machine Learning & AI",
    "Keras": "Machine Learning & AI",
    "Pandas": "Data Science",
    "NumPy": "Data Science",
    "Matplotlib": "Data Science",
    "Seaborn": "Data Science",
    "OpenCV": "Machine Learning & AI",
    "Hugging Face": "Machine Learning & AI",
    "LLM": "Machine Learning & AI",
    "LangChain": "Machine Learning & AI",
    "Data Analysis": "Data Science",
    "Statistics": "Data Science",
    "MLOps": "Machine Learning & AI",
    # Cloud & DevOps
    "AWS": "Cloud & DevOps",
    "Azure": "Cloud & DevOps",
    "GCP": "Cloud & DevOps",
    "Docker": "Cloud & DevOps",
    "Kubernetes": "Cloud & DevOps",
    "Terraform": "Cloud & DevOps",
    "Ansible": "Cloud & DevOps",
    "Jenkins": "Cloud & DevOps",
    "GitHub Actions": "Cloud & DevOps",
    "CI/CD": "Cloud & DevOps",
    "Linux": "Cloud & DevOps",
    "Git": "Cloud & DevOps",
    "Prometheus": "Cloud & DevOps",
    "Grafana": "Cloud & DevOps",
    "Nginx": "Cloud & DevOps",
    # Big Data & Analytics
    "Spark": "Big Data & Analytics",
    "Hadoop": "Big Data & Analytics",
    "Airflow": "Big Data & Analytics",
    "dbt": "Big Data & Analytics",
    "Power BI": "Big Data & Analytics",
    "Tableau": "Big Data & Analytics",
    "Excel": "Big Data & Analytics",
    # Mobile
    "React Native": "Mobile Development",
    "Flutter": "Mobile Development",
    "Firebase": "Mobile Development",
    "Supabase": "Backend & APIs",
    # Practices & Tooling
    "Agile": "Engineering Practices",
    "Scrum": "Engineering Practices",
    "Jira": "Engineering Practices",
    "OAuth": "Security & Architecture",
    "JWT": "Security & Architecture",
    "pytest": "Testing",
    "Selenium": "Testing",
    "Unit Testing": "Testing",
    "Microservices": "Architecture",
    "Hibernate": "Backend & APIs",
}


def seed_skills_taxonomy(db: Session) -> Dict[str, int]:
    """Insert all skill patterns from skill_extractor.py into the skills table.

    Skips duplicate skills if already present.
    Also ensures skills referenced in CAREER_PROFILES exist in the skills table.
    """
    # Fetch all existing skill canonical names in database
    existing_skills = {
        name.lower(): name for (name,) in db.query(Skill.canonical_name).all()
    }

    # Combine skill extractor patterns with skills listed in career profiles
    all_target_skills = list(SKILL_PATTERNS)
    for profile in CAREER_PROFILES.values():
        for req_skill in profile["required_skills"]:
            if req_skill not in all_target_skills:
                all_target_skills.append(req_skill)

    inserted_count = 0
    skipped_count = 0

    for skill_name in all_target_skills:
        clean_name = skill_name.strip()
        if not clean_name:
            continue

        lower_key = clean_name.lower()
        if lower_key in existing_skills:
            skipped_count += 1
            continue

        category = _SKILL_CATEGORIES.get(clean_name, "Technical Skills")
        new_skill = Skill(
            canonical_name=clean_name,
            category=category,
            version=1,
            status="active",
        )
        db.add(new_skill)
        existing_skills[lower_key] = clean_name
        inserted_count += 1

    db.commit()
    print(
        f"[Seeder] Skills taxonomy seeded: {inserted_count} added, {skipped_count} already existed."
    )
    return {"inserted": inserted_count, "skipped": skipped_count}


def seed_career_roles(db: Session) -> Dict[str, int]:
    """Insert all 10 career roles and their required skills into the database.

    - Inserts career roles into `career_roles` table.
    - Inserts required skills into `career_skills` table with importance weights (0.0 to 1.0).
    - Skips records if they already exist.
    """
    roles_inserted = 0
    roles_skipped = 0
    skills_linked = 0

    for role_name, profile_data in CAREER_PROFILES.items():
        # Check if career role already exists
        role = db.query(CareerRole).filter(CareerRole.name == role_name).first()
        if not role:
            role = CareerRole(
                name=role_name,
                description=str(profile_data["description"]),
                version=1,
            )
            db.add(role)
            db.flush()  # populate role.id
            roles_inserted += 1
        else:
            roles_skipped += 1

        required_skills: List[str] = profile_data["required_skills"]  # type: ignore
        total_skills = len(required_skills)

        for idx, raw_skill in enumerate(required_skills):
            # Calculate importance weight (ranges between 0.75 and 1.0 based on priority)
            importance = round(max(0.70, 1.0 - (idx * 0.04)), 2)

            # Find skill record by exact name, normalized name, or lowercase lookup
            skill = (
                db.query(Skill).filter(Skill.canonical_name == raw_skill).first()
            )
            if not skill:
                normalized = normalize_skill(raw_skill)
                skill = (
                    db.query(Skill)
                    .filter(Skill.canonical_name == normalized)
                    .first()
                )

            if not skill:
                # If skill is not yet in skills table, create it on the fly
                category = _SKILL_CATEGORIES.get(raw_skill, "Technical Skills")
                skill = Skill(
                    canonical_name=raw_skill,
                    category=category,
                    version=1,
                    status="active",
                )
                db.add(skill)
                db.flush()

            # Check if relationship already exists in career_skills
            existing_cs = (
                db.query(CareerSkill)
                .filter(
                    CareerSkill.career_id == role.id,
                    CareerSkill.skill_id == skill.id,
                )
                .first()
            )

            if not existing_cs:
                career_skill = CareerSkill(
                    career_id=role.id,
                    skill_id=skill.id,
                    importance=importance,
                    required=True,
                    weight=importance,
                )
                db.add(career_skill)
                skills_linked += 1

    db.commit()
    print(
        f"[Seeder] Career roles seeded: {roles_inserted} roles created, "
        f"{roles_skipped} roles existed, {skills_linked} career skills linked."
    )
    return {
        "roles_inserted": roles_inserted,
        "roles_skipped": roles_skipped,
        "skills_linked": skills_linked,
    }


def seed_all(db: Optional[Session] = None) -> Dict[str, Dict[str, int]]:
    """Seed both the skills taxonomy and career roles."""
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        skills_res = seed_skills_taxonomy(db)
        roles_res = seed_career_roles(db)
        return {"skills": skills_res, "roles": roles_res}
    finally:
        if close_after:
            db.close()


if __name__ == "__main__":
    print("Running database seeder...")
    result = seed_all()
    print("Seeding finished successfully:", result)

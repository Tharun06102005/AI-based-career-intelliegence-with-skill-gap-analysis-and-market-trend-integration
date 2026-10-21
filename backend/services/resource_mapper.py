"""Learning Resource Mapper service.

Curates comprehensive technical learning resources (courses, documentation,
tutorials, and books) mapped to technical skills, supporting targeted gap remediation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from sqlalchemy.orm import Session

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import Resource, Skill
from services.skill_normalizer import normalize_skill

# Curated library mapping 30+ core technical skills to verified learning resources
RESOURCE_LIBRARY: Dict[str, List[Dict[str, str]]] = {
    "Python": [
        {
            "title": "Python for Everybody Specialization",
            "url": "https://www.coursera.org/specializations/python",
            "provider": "Coursera / University of Michigan",
            "resource_type": "course",
        },
        {
            "title": "Real Python Learning Paths & Documentation",
            "url": "https://realpython.com/",
            "provider": "Real Python",
            "resource_type": "tutorial",
        },
        {
            "title": "Automate the Boring Stuff with Python",
            "url": "https://automatetheboringstuff.com/",
            "provider": "Al Sweigart",
            "resource_type": "book",
        },
    ],
    "JavaScript": [
        {
            "title": "MDN Web Docs: JavaScript Guide",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
            "provider": "Mozilla",
            "resource_type": "docs",
        },
        {
            "title": "The Modern JavaScript Tutorial",
            "url": "https://javascript.info/",
            "provider": "javascript.info",
            "resource_type": "tutorial",
        },
        {
            "title": "Eloquent JavaScript (3rd Edition)",
            "url": "https://eloquentjavascript.net/",
            "provider": "Marijn Haverbeke",
            "resource_type": "book",
        },
    ],
    "React": [
        {
            "title": "React Official Documentation (react.dev)",
            "url": "https://react.dev/",
            "provider": "Meta / React Team",
            "resource_type": "docs",
        },
        {
            "title": "Learn React Interactive Course",
            "url": "https://scrimba.com/learn/learnreact",
            "provider": "Scrimba",
            "resource_type": "course",
        },
        {
            "title": "Full Stack Open: Deep Dive Into Modern Web Development",
            "url": "https://fullstackopen.com/en/",
            "provider": "University of Helsinki",
            "resource_type": "course",
        },
    ],
    "SQL": [
        {
            "title": "SQLZoo Interactive SQL Platform",
            "url": "https://sqlzoo.net/",
            "provider": "SQLZoo",
            "resource_type": "tutorial",
        },
        {
            "title": "Mode Analytics SQL Tutorial for Data Analysis",
            "url": "https://mode.com/sql-tutorial/",
            "provider": "Mode Analytics",
            "resource_type": "tutorial",
        },
        {
            "title": "PostgreSQL Official Documentation",
            "url": "https://www.postgresql.org/docs/",
            "provider": "PostgreSQL Global Development Group",
            "resource_type": "docs",
        },
    ],
    "Docker": [
        {
            "title": "Docker Official Documentation",
            "url": "https://docs.docker.com/",
            "provider": "Docker",
            "resource_type": "docs",
        },
        {
            "title": "Play with Docker Classroom",
            "url": "https://training.play-with-docker.com/",
            "provider": "Docker",
            "resource_type": "tutorial",
        },
        {
            "title": "Docker Deep Dive",
            "url": "https://www.nigelpoulton.com/docker-deep-dive",
            "provider": "Nigel Poulton",
            "resource_type": "book",
        },
    ],
    "Machine Learning": [
        {
            "title": "Practical Deep Learning for Coders",
            "url": "https://course.fast.ai/",
            "provider": "fast.ai",
            "resource_type": "course",
        },
        {
            "title": "Machine Learning Specialization",
            "url": "https://www.coursera.org/specializations/machine-learning-introduction",
            "provider": "DeepLearning.AI / Stanford",
            "resource_type": "course",
        },
        {
            "title": "Scikit-Learn User Guide and API Reference",
            "url": "https://scikit-learn.org/stable/",
            "provider": "scikit-learn Developers",
            "resource_type": "docs",
        },
    ],
    "AWS": [
        {
            "title": "AWS Skill Builder Learning Plans",
            "url": "https://skillbuilder.aws/",
            "provider": "Amazon Web Services",
            "resource_type": "course",
        },
        {
            "title": "AWS Certified Solutions Architect Path",
            "url": "https://www.pluralsight.com/cloud-guru",
            "provider": "A Cloud Guru",
            "resource_type": "course",
        },
        {
            "title": "AWS Documentation & Architecture Center",
            "url": "https://docs.aws.amazon.com/",
            "provider": "Amazon Web Services",
            "resource_type": "docs",
        },
    ],
    "Git": [
        {
            "title": "Pro Git Book (2nd Edition)",
            "url": "https://git-scm.com/book/en/v2",
            "provider": "Scott Chacon & Ben Straub",
            "resource_type": "book",
        },
        {
            "title": "GitHub Skills Interactive Modules",
            "url": "https://skills.github.com/",
            "provider": "GitHub",
            "resource_type": "tutorial",
        },
        {
            "title": "Atlassian Git Workflows & Concepts",
            "url": "https://www.atlassian.com/git/tutorials",
            "provider": "Atlassian",
            "resource_type": "tutorial",
        },
    ],
    "TypeScript": [
        {
            "title": "TypeScript Official Handbook",
            "url": "https://www.typescriptlang.org/docs/",
            "provider": "Microsoft",
            "resource_type": "docs",
        },
        {
            "title": "Total TypeScript Essentials",
            "url": "https://www.totaltypescript.com/",
            "provider": "Matt Pocock",
            "resource_type": "tutorial",
        },
        {
            "title": "Execute Program: TypeScript Track",
            "url": "https://www.executeprogram.com/courses/typescript",
            "provider": "Execute Program",
            "resource_type": "course",
        },
    ],
    "Kubernetes": [
        {
            "title": "Kubernetes Official Documentation & Tasks",
            "url": "https://kubernetes.io/docs/home/",
            "provider": "Cloud Native Computing Foundation",
            "resource_type": "docs",
        },
        {
            "title": "Kubernetes Certified Administrator (CKA) Hands-On",
            "url": "https://kodekloud.com/courses/certified-kubernetes-administrator-cka/",
            "provider": "KodeKloud",
            "resource_type": "course",
        },
        {
            "title": "Kubernetes: Up and Running",
            "url": "https://www.oreilly.com/library/view/kubernetes-up-and/9781492046523/",
            "provider": "O'Reilly Media",
            "resource_type": "book",
        },
    ],
    "REST APIs": [
        {
            "title": "MDN HTTP & REST Architecture Guide",
            "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP",
            "provider": "Mozilla",
            "resource_type": "docs",
        },
        {
            "title": "Postman Learning Center & API Design Path",
            "url": "https://learning.postman.com/",
            "provider": "Postman",
            "resource_type": "tutorial",
        },
        {
            "title": "REST API Tutorial and Best Practices",
            "url": "https://restfulapi.net/",
            "provider": "RestfulAPI.net",
            "resource_type": "tutorial",
        },
    ],
    "TensorFlow": [
        {
            "title": "TensorFlow Official Core Tutorials",
            "url": "https://www.tensorflow.org/tutorials",
            "provider": "Google",
            "resource_type": "docs",
        },
        {
            "title": "TensorFlow Developer Professional Certificate",
            "url": "https://www.deeplearning.ai/courses/tensorflow-developer-professional-certificate/",
            "provider": "DeepLearning.AI",
            "resource_type": "course",
        },
        {
            "title": "Keras Developer Guides",
            "url": "https://keras.io/guides/",
            "provider": "Keras Team",
            "resource_type": "docs",
        },
    ],
    "Node.js": [
        {
            "title": "Node.js Official Documentation & API Reference",
            "url": "https://nodejs.org/en/docs/",
            "provider": "OpenJS Foundation",
            "resource_type": "docs",
        },
        {
            "title": "The Odin Project: NodeJS Curriculum",
            "url": "https://www.theodinproject.com/paths/full-stack-javascript/courses/nodejs",
            "provider": "The Odin Project",
            "resource_type": "course",
        },
        {
            "title": "NodeSchool Interactive Terminal Workshops",
            "url": "https://nodeschool.io/",
            "provider": "NodeSchool",
            "resource_type": "tutorial",
        },
    ],
    # Additional 17+ core skills
    "Java": [
        {
            "title": "Java Documentation & Learning Tutorials",
            "url": "https://dev.java/learn/",
            "provider": "Oracle",
            "resource_type": "docs",
        },
        {
            "title": "Java Programming Masterclass",
            "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/",
            "provider": "Tim Buchalka / Udemy",
            "resource_type": "course",
        },
        {
            "title": "Baeldung Spring & Java Guides",
            "url": "https://www.baeldung.com/",
            "provider": "Baeldung",
            "resource_type": "tutorial",
        },
    ],
    "PyTorch": [
        {
            "title": "PyTorch Official Tutorials & Recipes",
            "url": "https://pytorch.org/tutorials/",
            "provider": "PyTorch Foundation",
            "resource_type": "docs",
        },
        {
            "title": "Deep Learning with PyTorch: A 60 Minute Blitz",
            "url": "https://pytorch.org/tutorials/beginner/deep_learning_60min_blitz.html",
            "provider": "PyTorch",
            "resource_type": "tutorial",
        },
        {
            "title": "Deep Learning with PyTorch",
            "url": "https://www.manning.com/books/deep-learning-with-pytorch",
            "provider": "Manning Publications",
            "resource_type": "book",
        },
    ],
    "Pandas": [
        {
            "title": "Pandas Getting Started Tutorials",
            "url": "https://pandas.pydata.org/docs/getting_started/index.html",
            "provider": "pandas development team",
            "resource_type": "docs",
        },
        {
            "title": "Python for Data Analysis",
            "url": "https://wesmckinney.com/book/",
            "provider": "Wes McKinney",
            "resource_type": "book",
        },
        {
            "title": "Data Analysis with Python and Pandas",
            "url": "https://www.freecodecamp.org/news/how-to-analyze-data-with-python-pandas/",
            "provider": "freeCodeCamp",
            "resource_type": "tutorial",
        },
    ],
    "FastAPI": [
        {
            "title": "FastAPI Official Documentation & Tutorial",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "provider": "Sebastián Ramírez",
            "resource_type": "docs",
        },
        {
            "title": "Test-Driven Development with FastAPI and Docker",
            "url": "https://testdriven.io/courses/fastapi-crud/",
            "provider": "TestDriven.io",
            "resource_type": "course",
        },
    ],
    "Linux": [
        {
            "title": "Linux Journey: Learn Linux Step-by-Step",
            "url": "https://linuxjourney.com/",
            "provider": "Linux Journey",
            "resource_type": "tutorial",
        },
        {
            "title": "The Linux Command Line",
            "url": "https://linuxcommand.org/tlcl.php",
            "provider": "William Shotts",
            "resource_type": "book",
        },
        {
            "title": "Introduction to Linux (LFS101x)",
            "url": "https://www.edx.org/learn/linux/the-linux-foundation-introduction-to-linux",
            "provider": "The Linux Foundation",
            "resource_type": "course",
        },
    ],
    "Terraform": [
        {
            "title": "HashiCorp Terraform Documentation & Tutorials",
            "url": "https://developer.hashicorp.com/terraform/tutorials",
            "provider": "HashiCorp",
            "resource_type": "docs",
        },
        {
            "title": "Terraform: Up & Running",
            "url": "https://www.terraformupandrunning.com/",
            "provider": "Yevgeniy Brikman",
            "resource_type": "book",
        },
    ],
    "CI/CD": [
        {
            "title": "GitHub Actions Documentation & Workflows",
            "url": "https://docs.github.com/en/actions",
            "provider": "GitHub",
            "resource_type": "docs",
        },
        {
            "title": "Continuous Delivery: Reliable Software Releases",
            "url": "https://continuousdelivery.com/",
            "provider": "Jez Humble & David Farley",
            "resource_type": "book",
        },
        {
            "title": "GitLab CI/CD Fundamentals",
            "url": "https://docs.gitlab.com/ee/ci/",
            "provider": "GitLab",
            "resource_type": "tutorial",
        },
    ],
    "Redis": [
        {
            "title": "Redis University Free Courses",
            "url": "https://university.redis.com/",
            "provider": "Redis",
            "resource_type": "course",
        },
        {
            "title": "Redis Official Documentation & Data Structures",
            "url": "https://redis.io/docs/",
            "provider": "Redis",
            "resource_type": "docs",
        },
    ],
    "PostgreSQL": [
        {
            "title": "PostgreSQL Tutorial for Beginners",
            "url": "https://www.postgresqltutorial.com/",
            "provider": "PostgreSQL Tutorial",
            "resource_type": "tutorial",
        },
        {
            "title": "The Art of PostgreSQL",
            "url": "https://theartofpostgresql.com/",
            "provider": "Dimitri Fontaine",
            "resource_type": "book",
        },
    ],
    "MongoDB": [
        {
            "title": "MongoDB University Learning Paths",
            "url": "https://learn.mongodb.com/",
            "provider": "MongoDB",
            "resource_type": "course",
        },
        {
            "title": "MongoDB Manual & Documentation",
            "url": "https://www.mongodb.com/docs/",
            "provider": "MongoDB",
            "resource_type": "docs",
        },
    ],
    "Next.js": [
        {
            "title": "Next.js Learn Interactive Course",
            "url": "https://nextjs.org/learn",
            "provider": "Vercel",
            "resource_type": "course",
        },
        {
            "title": "Next.js Official Documentation",
            "url": "https://nextjs.org/docs",
            "provider": "Vercel",
            "resource_type": "docs",
        },
    ],
    "HTML": [
        {
            "title": "MDN HTML: Structuring the Web",
            "url": "https://developer.mozilla.org/en-US/docs/Learn/HTML",
            "provider": "Mozilla",
            "resource_type": "docs",
        },
        {
            "title": "Responsive Web Design Certification",
            "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
            "provider": "freeCodeCamp",
            "resource_type": "course",
        },
    ],
    "CSS": [
        {
            "title": "MDN CSS: Styling the Web",
            "url": "https://developer.mozilla.org/en-US/docs/Learn/CSS",
            "provider": "Mozilla",
            "resource_type": "docs",
        },
        {
            "title": "CSS-Tricks Guides and Almanac",
            "url": "https://css-tricks.com/",
            "provider": "CSS-Tricks",
            "resource_type": "tutorial",
        },
    ],
    "LLM": [
        {
            "title": "DeepLearning.AI: Generative AI with LLMs",
            "url": "https://www.deeplearning.ai/courses/generative-ai-with-llms/",
            "provider": "DeepLearning.AI / AWS",
            "resource_type": "course",
        },
        {
            "title": "LangChain Official Documentation",
            "url": "https://python.langchain.com/docs/get_started/introduction",
            "provider": "LangChain",
            "resource_type": "docs",
        },
    ],
    "OpenCV": [
        {
            "title": "OpenCV Python Tutorials",
            "url": "https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html",
            "provider": "OpenCV Team",
            "resource_type": "docs",
        },
        {
            "title": "PyImageSearch Computer Vision Guides",
            "url": "https://pyimagesearch.com/",
            "provider": "Adrian Rosebrock",
            "resource_type": "tutorial",
        },
    ],
    "NLP": [
        {
            "title": "Hugging Face NLP Course",
            "url": "https://huggingface.co/learn/nlp-course/",
            "provider": "Hugging Face",
            "resource_type": "course",
        },
        {
            "title": "Natural Language Processing with Transformers",
            "url": "https://www.oreilly.com/library/view/natural-language-processing/9781098103231/",
            "provider": "O'Reilly Media",
            "resource_type": "book",
        },
    ],
    "Power BI": [
        {
            "title": "Microsoft Power BI Guided Learning",
            "url": "https://learn.microsoft.com/en-us/training/powerplatform/power-bi",
            "provider": "Microsoft Learn",
            "resource_type": "course",
        },
        {
            "title": "Guy in a Cube Power BI Tutorials",
            "url": "https://guyinacube.com/",
            "provider": "Guy in a Cube",
            "resource_type": "tutorial",
        },
    ],
    "Tableau": [
        {
            "title": "Tableau Free Training Videos",
            "url": "https://www.tableau.com/learn/training",
            "provider": "Tableau",
            "resource_type": "tutorial",
        },
        {
            "title": "Tableau Desktop Specialist Preparation",
            "url": "https://www.coursera.org/specializations/data-visualization",
            "provider": "UC Davis / Coursera",
            "resource_type": "course",
        },
    ],
    "Excel": [
        {
            "title": "Excel for Windows Training & Support",
            "url": "https://support.microsoft.com/en-us/excel",
            "provider": "Microsoft Support",
            "resource_type": "docs",
        },
        {
            "title": "Chandoo Excel and Advanced Formulas",
            "url": "https://chandoo.org/",
            "provider": "Chandoo",
            "resource_type": "tutorial",
        },
    ],
    "Go": [
        {
            "title": "A Tour of Go Interactive",
            "url": "https://go.dev/tour/",
            "provider": "Go Team",
            "resource_type": "tutorial",
        },
        {
            "title": "Go Documentation and Standard Library",
            "url": "https://go.dev/doc/",
            "provider": "Google",
            "resource_type": "docs",
        },
    ],
}


def get_resources_for_skill(skill_name: str) -> List[Dict[str, str]]:
    """Return verified learning resources for a specific skill.

    Matches exact name, case-insensitively, or via canonical normalization.
    Generates sensible fallback documentation and tutorial links if not in dictionary.
    """
    if not skill_name or not isinstance(skill_name, str):
        return []

    clean = skill_name.strip()
    norm = normalize_skill(clean)

    # 1. Exact match
    if clean in RESOURCE_LIBRARY:
        return [dict(r, skill_name=clean) for r in RESOURCE_LIBRARY[clean]]

    # 2. Canonical normalized match
    if norm in RESOURCE_LIBRARY:
        return [dict(r, skill_name=norm) for r in RESOURCE_LIBRARY[norm]]

    # 3. Case-insensitive lookup
    for key, items in RESOURCE_LIBRARY.items():
        if key.lower() == clean.lower() or key.lower() == norm.lower():
            return [dict(r, skill_name=key) for r in items]

    # 4. Standard fallback for uncataloged skills
    return [
        {
            "skill_name": clean,
            "title": f"{clean} Official Documentation & Getting Started",
            "url": f"https://www.google.com/search?q={clean}+official+documentation",
            "provider": "Official Documentation",
            "resource_type": "docs",
        },
        {
            "skill_name": clean,
            "title": f"Hands-on {clean} Practice Tutorial",
            "url": f"https://www.google.com/search?q={clean}+tutorial+for+beginners",
            "provider": "Developer Community",
            "resource_type": "tutorial",
        },
    ]


def get_resources_for_gaps(
    missing_skills: Sequence[str],
) -> Dict[str, List[Dict[str, str]]]:
    """Map each missing technical skill to its list of recommended resources."""
    gap_resources: Dict[str, List[Dict[str, str]]] = {}
    for skill in missing_skills:
        clean = str(skill).strip()
        if clean:
            gap_resources[clean] = get_resources_for_skill(clean)
    return gap_resources


def ensure_resources_in_db(db: Session) -> Dict[str, int]:
    """Seed or synchronize resource library records into the database `resources` table.

    Guarantees every mapped resource has a valid database integer id for progress tracking.
    """
    skills_map = {
        s.canonical_name.lower(): s for s in db.query(Skill).all()
    }

    inserted = 0
    existing_count = 0

    for skill_name, resources in RESOURCE_LIBRARY.items():
        s_obj = skills_map.get(skill_name.lower()) or skills_map.get(normalize_skill(skill_name).lower())
        if not s_obj:
            s_obj = Skill(canonical_name=skill_name, category="Technical Skills")
            db.add(s_obj)
            db.flush()
            skills_map[skill_name.lower()] = s_obj

        for r in resources:
            title = r["title"]
            db_res = (
                db.query(Resource)
                .filter(Resource.skill_id == s_obj.id, Resource.title == title)
                .first()
            )
            if not db_res:
                db_res = Resource(
                    skill_id=s_obj.id,
                    title=title,
                    url=r.get("url"),
                    provider=r.get("provider"),
                    resource_type=r.get("resource_type", "docs"),
                )
                db.add(db_res)
                inserted += 1
            else:
                existing_count += 1

    db.commit()
    return {"inserted": inserted, "existing": existing_count}

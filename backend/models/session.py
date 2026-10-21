"""Database engine, session factory, and FastAPI dependency.

Sync SQLAlchemy 2.0 session backed by psycopg2 (per the pinned
requirements.txt). DATABASE_URL is loaded from the project-root .env file
via core.config.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from .database import Base  # noqa: F401  re-exported for convenience

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a Session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "engine", "SessionLocal", "get_db"]

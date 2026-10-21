"""Alembic migration environment for the career-intelligence backend.

Imports every model from backend/models/database.py so that autogenerate and
upgrade both see the full 20-table schema.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `backend/` importable so `models` and `core` resolve from any cwd.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import Base  # noqa: E402
import models  # noqa: F401,E402  registers all 20 model classes on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve URL: shell env > .env (pydantic settings) > alembic.ini."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    try:
        from core.config import settings

        if settings.database_url:
            return settings.database_url
    except Exception:
        pass
    return config.get_section(config.config_ini_section, {}).get("sqlalchemy.url", "")


url = _database_url()
if url:
    config.set_section_option(config.config_ini_section, "sqlalchemy.url", url)


def run_migrations_offline() -> None:
    """Run migrations in --offline mode (emit SQL without a DB connection)."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Application settings loaded from the project-root .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/core/config.py -> parents[0]=core, [1]=backend, [2]=project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Pydantic Settings backed by the .env file at the project root."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    groq_api_key: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    environment: str = "development"


settings = Settings()

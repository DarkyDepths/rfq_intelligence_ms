"""
settings.py — Application Configuration

BACAB Layer: Config (cross-cutting)

Responsibility:
    Loads environment variables via pydantic-settings and provides
    typed access throughout the application: `settings.DATABASE_URL`.

Current status: COMPLETE for skeleton.
"""

from pydantic import ValidationError
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url


class Settings(BaseSettings):

    # ── Required ──────────────────────────────────────
    DATABASE_URL: str

    # ── Optional with defaults ────────────────────────
    APP_NAME: str = "rfq_intelligence_ms"
    APP_PORT: int = 8001
    APP_DEBUG: bool = False
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "*"
    MANAGER_MS_BASE_URL: str = "http://localhost:18000"
    MANAGER_REQUEST_TIMEOUT_SECONDS: float = 10.0
    MANAGER_UPLOADS_MOUNT_PATH: str = "/app/manager_uploads"

    class Config:
        env_file = ".env"


def build_settings(env_file: str | None = ".env") -> Settings:
    """Load app settings and fail fast with clear DB configuration errors."""
    try:
        cfg = Settings(_env_file=env_file)
    except ValidationError as exc:
        raise RuntimeError(
            "Configuration error: DATABASE_URL is required. "
            "Set DATABASE_URL to a valid SQLAlchemy URL, for example: "
            "postgresql+psycopg2://intelligence_user:intelligence_pass@localhost:5433/rfq_intelligence_db"
        ) from exc

    database_url = (cfg.DATABASE_URL or "").strip()
    if not database_url:
        raise RuntimeError(
            "Configuration error: DATABASE_URL is required and cannot be empty. "
            "Set DATABASE_URL to a valid SQLAlchemy URL, for example: "
            "postgresql+psycopg2://intelligence_user:intelligence_pass@localhost:5433/rfq_intelligence_db"
        )

    try:
        make_url(database_url)
    except Exception as exc:
        raise RuntimeError(
            f"Configuration error: DATABASE_URL is not a valid SQLAlchemy URL: '{database_url}'. "
            "Example: postgresql+psycopg2://intelligence_user:intelligence_pass@localhost:5433/rfq_intelligence_db"
        ) from exc

    return cfg


# ── Module-level instance ─────────────────────────────
settings = build_settings()

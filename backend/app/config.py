"""Application configuration.

All settings are loaded from environment variables (or the project-root `.env`
file during local development). Secrets must never be hardcoded here — see
`.env.example` for the expected variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo root is two levels up from this file: backend/app/config.py -> SmartWrite/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed view over the environment.

    Only `DATABASE_URL` is needed for the backend skeleton (item 1). The other
    fields are declared now so the app boots cleanly once they're populated in
    `.env`, and so we have a single source of truth as later features land.
    """

    # --- App ---
    app_name: str = "SmartWrite API"
    debug: bool = False

    # --- Database ---
    # Async driver URLs: "sqlite+aiosqlite:///./smartwrite.db" locally,
    # "postgresql+asyncpg://..." in production (set via Render env var).
    database_url: str = "sqlite+aiosqlite:///./smartwrite.db"

    # --- Secrets (used by later milestones; optional for the skeleton) ---
    secret_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    history_encryption_key: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # tolerate unrelated vars in .env
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment only once)."""
    return Settings()

"""Application configuration.

All settings are loaded from environment variables (or the project-root `.env`
file during local development). Secrets must never be hardcoded here — see
`.env.example` for the expected variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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

    # --- Secrets ---
    secret_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    history_encryption_key: str = ""

    @field_validator("database_url")
    @classmethod
    def fix_async_driver(cls, v: str) -> str:
        # Render Postgres connection strings arrive as postgres:// or postgresql://.
        # Rewrite both to the asyncpg scheme SQLAlchemy requires.
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://"):]
        elif v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]

        # Reject any remaining Postgres URL that uses a non-asyncpg driver
        # (e.g. postgresql+psycopg://) — these pass the rewrites above silently
        # but fail later inside create_async_engine() with a confusing error.
        if v.startswith("postgresql") and not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL uses an unsupported PostgreSQL driver. "
                "Use postgresql+asyncpg://, or bare postgresql:// / postgres:// "
                "(auto-rewritten). "
                f"Got scheme: {v.split('://')[0]}://"
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # tolerate unrelated vars in .env
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment only once)."""
    return Settings()

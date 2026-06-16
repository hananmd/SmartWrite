"""SmartWrite FastAPI application entrypoint.

Run locally from the project root:

    uvicorn backend.app.main:app --reload

This is the skeleton (PROGRESS.md item 1): app instance, lifespan-managed DB
engine, and a health endpoint. Auth, correction, and history routers are added
in later milestones.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.database import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage resources tied to the app's lifecycle.

    On startup we just hold the engine open; on shutdown we dispose it so
    pooled connections are closed cleanly. Schema creation is handled by
    Alembic migrations, not here.
    """
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness + DB connectivity check.

    Returns ok only if a trivial query against the configured database
    succeeds — useful as a Render health check and a local smoke test.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}

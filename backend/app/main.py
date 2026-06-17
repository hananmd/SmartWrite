"""SmartWrite FastAPI application entrypoint.

Run locally from the project root:

    uvicorn backend.app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.routers import auth as auth_router
from backend.app.routers import correct as correct_router

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

app.include_router(auth_router.router)
app.include_router(correct_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness + DB connectivity check.

    Returns ok only if a trivial query against the configured database
    succeeds — useful as a Render health check and a local smoke test.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}

"""SmartWrite FastAPI application entrypoint.

Run locally from the project root:

    uvicorn backend.app.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.routers import auth as auth_router
from backend.app.routers import correct as correct_router
from backend.app.routers import history as history_router

FRONTEND_DIR = Path(__file__).parents[2] / "frontend"

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

# Allow cross-origin requests from the Chrome extension (which uses Bearer tokens,
# not cookies). allow_credentials must be False when allow_origins is "*".
# The PWA is same-origin so CORS headers are irrelevant for it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router.router)
app.include_router(correct_router.router)
app.include_router(history_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness + DB connectivity check.

    Returns ok only if a trivial query against the configured database
    succeeds — useful as a Render health check and a local smoke test.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


# Mount the PWA static files last so API routes always take priority.
# Guarded so the app still boots if the frontend directory is absent (e.g. API-only deploys).
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

"""
Pytest configuration for SmartWrite backend tests.

ENV VARS ARE SET AT THE TOP OF THIS FILE before any backend import so that
the lru_cached Settings instance and _fernet() pick up test values, not the
real .env file.

DB strategy: a named temp file + NullPool avoids the in-memory-per-connection
isolation problem with aiosqlite and sidesteps event-loop-binding issues that
arise when asyncio.run() and pytest-asyncio use separate loops.
"""
import asyncio
import os
import tempfile

from cryptography.fernet import Fernet

# ── Must precede ALL backend imports ─────────────────────────────────────────
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_DB_PATH = _tmp.name
_tmp.close()

os.environ["SECRET_KEY"] = "test-secret-key-for-smartwrite-pytest-only-xxxxx!"
os.environ["HISTORY_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["DEBUG"] = "true"
# ─────────────────────────────────────────────────────────────────────────────

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.database import Base, get_db
from backend.app.main import app

# Clear any stale cached Settings that loaded before our env vars were set.
get_settings.cache_clear()

# Separate test engine using NullPool (no pooled connections = no event-loop binding).
_test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    future=True,
    poolclass=NullPool,
)
_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


# ── Table lifecycle ───────────────────────────────────────────────────────────

async def _create_all() -> None:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_all() -> None:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _tables() -> None:
    """Create all tables once for the test session; drop them on teardown."""
    asyncio.run(_create_all())
    yield
    asyncio.run(_drop_all())


# ── Direct DB access for tests that verify storage ───────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """Yield a raw AsyncSession against the test engine for storage-level assertions."""
    async with _TestSession() as session:
        yield session


# ── HTTP test client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Async HTTPX client wired to the FastAPI ASGI app, DB overridden to test engine."""
    async def _override_db():
        async with _TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

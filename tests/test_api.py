"""
Integration tests for all SmartWrite HTTP endpoints.

Each test that needs auth uses a unique email so tests don't conflict
in the shared session-scoped test database.

Groq calls are mocked at the router's import binding
(backend.app.routers.correct.correct_text) so no real API key is needed.
"""
from unittest.mock import AsyncMock, patch

import pytest

_MOCK_GROQ = {
    "detected_tone": "casual",
    "applied_tone": "formal",
    "corrected_text": "This is a corrected sentence.",
    "changes_summary": "Applied formal tone and fixed grammar.",
}


# ── /health ───────────────────────────────────────────────────────────────────

async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── /api/register ─────────────────────────────────────────────────────────────

async def test_register_returns_201_and_token(client):
    r = await client.post("/api/register", json={
        "email": "reg1@example.com",
        "password": "Password123!",
    })
    assert r.status_code == 201
    assert "access_token" in r.json()


async def test_register_duplicate_email_returns_409(client):
    body = {"email": "dup@example.com", "password": "Password123!"}
    await client.post("/api/register", json=body)
    r = await client.post("/api/register", json=body)
    assert r.status_code == 409


async def test_register_invalid_email_returns_422(client):
    r = await client.post("/api/register", json={
        "email": "not-an-email",
        "password": "Password123!",
    })
    assert r.status_code == 422


async def test_register_missing_password_returns_422(client):
    r = await client.post("/api/register", json={"email": "nopw@example.com"})
    assert r.status_code == 422


# ── /api/login ────────────────────────────────────────────────────────────────

async def test_login_success_returns_200_and_token(client):
    creds = {"email": "login_ok@example.com", "password": "Password123!"}
    await client.post("/api/register", json=creds)
    r = await client.post("/api/login", json=creds)
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_wrong_password_returns_401(client):
    await client.post("/api/register", json={
        "email": "login_bad@example.com", "password": "correct",
    })
    r = await client.post("/api/login", json={
        "email": "login_bad@example.com", "password": "wrong",
    })
    assert r.status_code == 401


async def test_login_unknown_email_returns_401(client):
    r = await client.post("/api/login", json={
        "email": "nobody@example.com", "password": "password",
    })
    assert r.status_code == 401


# ── /api/me ───────────────────────────────────────────────────────────────────

async def test_me_authenticated_returns_user_email(client):
    reg = await client.post("/api/register", json={
        "email": "me_ok@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    r = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "me_ok@example.com"


async def test_me_no_token_returns_401(client):
    r = await client.get("/api/me")
    assert r.status_code == 401


async def test_me_invalid_token_returns_401(client):
    r = await client.get("/api/me", headers={"Authorization": "Bearer bad.token.here"})
    assert r.status_code == 401


# ── /api/logout ───────────────────────────────────────────────────────────────

async def test_logout_returns_200(client):
    r = await client.post("/api/logout")
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out"


# ── /api/correct ──────────────────────────────────────────────────────────────

async def test_correct_unauthenticated_returns_401(client):
    r = await client.post("/api/correct", json={"text": "hello", "tone": "formal"})
    assert r.status_code == 401


async def test_correct_invalid_tone_returns_422(client):
    reg = await client.post("/api/register", json={
        "email": "correct_tone@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    r = await client.post(
        "/api/correct",
        json={"text": "hello", "tone": "robot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_correct_empty_text_returns_422(client):
    reg = await client.post("/api/register", json={
        "email": "correct_empty@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    r = await client.post(
        "/api/correct",
        json={"text": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_correct_success_returns_corrected_text(client):
    reg = await client.post("/api/register", json={
        "email": "correct_ok@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]

    with patch(
        "backend.app.routers.correct.correct_text",
        new_callable=AsyncMock,
        return_value=_MOCK_GROQ,
    ):
        r = await client.post(
            "/api/correct",
            json={"text": "hey wuts up", "tone": "formal"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["corrected_text"] == "This is a corrected sentence."
    assert data["applied_tone"] == "formal"
    assert data["detected_tone"] == "casual"
    assert data["warning"] is None


async def test_correct_groq_down_returns_503(client):
    from backend.app.groq_client import GroqUnavailableError

    reg = await client.post("/api/register", json={
        "email": "correct_503@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]

    with patch(
        "backend.app.routers.correct.correct_text",
        new_callable=AsyncMock,
        side_effect=GroqUnavailableError("Service down"),
    ):
        r = await client.post(
            "/api/correct",
            json={"text": "some text"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 503


# ── /api/history ──────────────────────────────────────────────────────────────

async def test_history_unauthenticated_returns_401(client):
    r = await client.get("/api/history")
    assert r.status_code == 401


async def test_history_empty_for_new_user(client):
    reg = await client.post("/api/register", json={
        "email": "hist_empty@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    r = await client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_history_appears_after_correction(client):
    reg = await client.post("/api/register", json={
        "email": "hist_fill@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.routers.correct.correct_text",
        new_callable=AsyncMock,
        return_value=_MOCK_GROQ,
    ):
        await client.post("/api/correct", json={"text": "hello world"}, headers=headers)

    r = await client.get("/api/history", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["original_text"] == "hello world"
    assert data["items"][0]["corrected_text"] == "This is a corrected sentence."
    assert data["items"][0]["tone"] == "formal"


async def test_history_pagination_limit(client):
    reg = await client.post("/api/register", json={
        "email": "hist_page@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.routers.correct.correct_text",
        new_callable=AsyncMock,
        return_value=_MOCK_GROQ,
    ):
        for _ in range(3):
            await client.post("/api/correct", json={"text": "test"}, headers=headers)

    r = await client.get("/api/history?limit=2&offset=0", headers=headers)
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


# ── /api/analytics ────────────────────────────────────────────────────────────

async def test_analytics_unauthenticated_returns_401(client):
    r = await client.get("/api/analytics")
    assert r.status_code == 401


async def test_analytics_empty_for_new_user(client):
    reg = await client.post("/api/register", json={
        "email": "analytics_empty@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    r = await client.get("/api/analytics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_corrections"] == 0
    assert data["most_used_tone"] is None
    assert data["corrections_per_tone"] == []
    assert data["corrections_last_7_days"] == 0


async def test_analytics_totals_after_corrections(client):
    reg = await client.post("/api/register", json={
        "email": "analytics_fill@example.com", "password": "Password123!",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "backend.app.routers.correct.correct_text",
        new_callable=AsyncMock,
        return_value=_MOCK_GROQ,
    ):
        await client.post("/api/correct", json={"text": "one"}, headers=headers)
        await client.post("/api/correct", json={"text": "two"}, headers=headers)

    r = await client.get("/api/analytics", headers=headers)
    data = r.json()
    assert data["total_corrections"] == 2
    assert data["most_used_tone"] == "formal"
    assert data["corrections_last_7_days"] == 2

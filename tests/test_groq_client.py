"""
Unit tests for groq_client.py.

All HTTP calls are mocked so these tests run offline and instantly.
The retry-count assertions also act as regression tests for the
off-by-one bug that was fixed (attempt == max_retries-1 → >= max_retries),
ensuring 4 total attempts are made before giving up.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.groq_client import VALID_TONES, GroqUnavailableError, correct_text


# ── Helpers ───────────────────────────────────────────────────────────────────

def _http_response(status: int, json_data=None) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    if json_data is not None:
        m.json.return_value = json_data
    return m


def _groq_json(
    detected: str = "casual",
    applied: str = "formal",
    text: str = "Corrected.",
    summary: str = "Fixed grammar.",
) -> dict:
    content = json.dumps({
        "detected_tone": detected,
        "applied_tone": applied,
        "corrected_text": text,
        "changes_summary": summary,
    })
    return {"choices": [{"message": {"content": content}}]}


def _mock_ctx(response) -> tuple[MagicMock, AsyncMock]:
    """Return (context_manager_mock, client_mock) where client.post → response."""
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


# ── Tone validation ───────────────────────────────────────────────────────────

async def test_invalid_tone_raises_value_error():
    with pytest.raises(ValueError, match="Invalid tone"):
        await correct_text("some text", "robot_voice")


async def test_none_tone_is_accepted():
    ctx, _ = _mock_ctx(_http_response(200, _groq_json()))
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await correct_text("hello world", None)
    assert "corrected_text" in result


async def test_all_valid_tones_pass_validation():
    for tone in VALID_TONES:
        ctx, _ = _mock_ctx(_http_response(200, _groq_json(applied=tone)))
        with patch("httpx.AsyncClient", return_value=ctx):
            result = await correct_text("hello", tone)
        assert result["applied_tone"] == tone


# ── Missing API key ───────────────────────────────────────────────────────────

async def test_missing_api_key_raises_unavailable():
    with patch("backend.app.groq_client.get_settings") as mock_gs:
        mock_gs.return_value.groq_api_key = ""
        mock_gs.return_value.groq_model = "test-model"
        with pytest.raises(GroqUnavailableError, match="not configured"):
            await correct_text("text")


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_successful_response_returns_all_keys():
    ctx, _ = _mock_ctx(_http_response(200, _groq_json()))
    with patch("httpx.AsyncClient", return_value=ctx):
        result = await correct_text("hey wuts up", "formal")
    assert result == {
        "detected_tone": "casual",
        "applied_tone": "formal",
        "corrected_text": "Corrected.",
        "changes_summary": "Fixed grammar.",
    }


# ── Retry behaviour (also validates the off-by-one fix) ──────────────────────

async def test_rate_limit_retries_4_times_then_raises():
    ctx, client_mock = _mock_ctx(_http_response(429))
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(GroqUnavailableError, match="Rate limit"):
            await correct_text("text", "formal")
    assert client_mock.post.call_count == 4  # 1 initial + 3 retries


async def test_server_error_retries_4_times_then_raises():
    ctx, client_mock = _mock_ctx(_http_response(500))
    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(GroqUnavailableError, match="experiencing issues"):
            await correct_text("text", "formal")
    assert client_mock.post.call_count == 4


async def test_connection_error_retries_4_times_then_raises():
    client_mock = AsyncMock()
    client_mock.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client_mock)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(GroqUnavailableError, match="unavailable"):
            await correct_text("text", "formal")
    assert client_mock.post.call_count == 4


async def test_success_after_one_retry():
    client_mock = AsyncMock()
    client_mock.post = AsyncMock(
        side_effect=[_http_response(429), _http_response(200, _groq_json())]
    )
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client_mock)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=ctx), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await correct_text("hello", "formal")

    assert result["corrected_text"] == "Corrected."
    assert client_mock.post.call_count == 2


# ── Malformed responses ───────────────────────────────────────────────────────

async def test_missing_required_keys_raises_unavailable():
    bad_payload = {"choices": [{"message": {"content": json.dumps({"detected_tone": "casual"})}}]}
    ctx, _ = _mock_ctx(_http_response(200, bad_payload))
    with patch("httpx.AsyncClient", return_value=ctx):
        with pytest.raises(GroqUnavailableError, match="incomplete"):
            await correct_text("text", "formal")


async def test_non_json_content_raises_unavailable():
    bad_payload = {"choices": [{"message": {"content": "not json at all {"}}]}
    ctx, _ = _mock_ctx(_http_response(200, bad_payload))
    with patch("httpx.AsyncClient", return_value=ctx):
        with pytest.raises(GroqUnavailableError, match="unexpected response"):
            await correct_text("text", "formal")


async def test_unexpected_http_status_raises_unavailable():
    ctx, _ = _mock_ctx(_http_response(404))
    with patch("httpx.AsyncClient", return_value=ctx):
        with pytest.raises(GroqUnavailableError, match="Unexpected error"):
            await correct_text("text", "formal")

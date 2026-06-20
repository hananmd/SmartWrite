"""Groq API client: tone detection, grammar correction, and text rewriting.

Uses httpx (already a dependency) against Groq's OpenAI-compatible endpoint.
Retry strategy: up to 3 attempts with exponential backoff (1s, 2s, 4s) on
429 rate-limit and 5xx server errors. All failure paths raise GroqUnavailableError
with a user-facing message so routers never surface raw stack traces.

Never log raw user text, API keys, or JWT tokens — see CLAUDE.md security rules.
"""

import asyncio
import json
import logging
from typing import Any

import httpx

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

VALID_TONES = frozenset({"formal", "casual", "friendly", "professional"})

_SYSTEM_PROMPT = (
    "You are a writing assistant. Given a piece of text you will:\n"
    "1. Detect its current tone (one of: formal, casual, friendly, professional, neutral).\n"
    "2. Apply the requested target tone — rewrite with that tone.\n"
    "3. Fix all grammar and spelling errors.\n"
    "4. Respond with ONLY a JSON object containing exactly these four keys:\n"
    '   "detected_tone"   — the tone you detected in the original text\n'
    '   "applied_tone"    — the tone you applied in the corrected text\n'
    '   "corrected_text"  — the grammar-corrected, tone-adjusted version\n'
    '   "changes_summary" — one sentence summarising the main changes made\n'
    "No markdown fences, no explanation outside the JSON object."
)


class GroqUnavailableError(Exception):
    """Raised when Groq is unreachable, rate-limited beyond retries, or misbehaving."""

    def __init__(self, user_message: str) -> None:
        self.user_message = user_message
        super().__init__(user_message)


async def correct_text(text: str, tone: str | None = None) -> dict[str, Any]:
    """Call Groq to detect tone, correct grammar, and rewrite text.

    Args:
        text: The user's raw input text (1–5 000 chars).
        tone: Optional target tone. Must be one of VALID_TONES if supplied.
              If None the model picks the most appropriate tone.

    Returns:
        Dict with keys: detected_tone, applied_tone, corrected_text, changes_summary.

    Raises:
        GroqUnavailableError: If the service is down or rate-limited after all retries.
        ValueError: If *tone* is not a recognised value.
    """
    settings = get_settings()

    if not settings.groq_api_key:
        raise GroqUnavailableError(
            "AI service is not configured. Please contact the administrator."
        )

    if tone is not None:
        tone = tone.lower()
        if tone not in VALID_TONES:
            raise ValueError(
                f"Invalid tone '{tone}'. Must be one of: {', '.join(sorted(VALID_TONES))}"
            )

    tone_instruction = (
        f"Apply the '{tone}' tone."
        if tone
        else "Recommend and apply the most appropriate tone for this text."
    )

    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"{tone_instruction}\n\nText:\n{text}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    max_retries = 3
    max_attempts = max_retries + 1
    base_backoff = 1.0  # retry backoff: 1s, 2s, 4s

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_attempts):
            try:
                response = await client.post(_GROQ_URL, json=payload, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.warning("Groq connection error (attempt %d/%d)", attempt + 1, max_attempts)
                if attempt >= max_retries:
                    raise GroqUnavailableError(
                        "The AI writing service is temporarily unavailable. Please try again in a moment."
                    ) from exc
                await asyncio.sleep(base_backoff * (2**attempt))
                continue

            if response.status_code == 429:
                logger.warning("Groq rate limit hit (attempt %d/%d)", attempt + 1, max_attempts)
                if attempt >= max_retries:
                    raise GroqUnavailableError(
                        "Rate limit reached. Please wait a moment and try again."
                    )
                await asyncio.sleep(base_backoff * (2**attempt))
                continue

            if response.status_code >= 500:
                logger.warning(
                    "Groq server error %d (attempt %d/%d)",
                    response.status_code,
                    attempt + 1,
                    max_attempts,
                )
                if attempt >= max_retries:
                    raise GroqUnavailableError(
                        "The AI service is experiencing issues. Please try again shortly."
                    )
                await asyncio.sleep(base_backoff * (2**attempt))
                continue

            if response.status_code != 200:
                logger.error("Unexpected Groq status %d", response.status_code)
                raise GroqUnavailableError(
                    "Unexpected error from the AI service. Please try again."
                )

            # Happy path — parse the model's JSON reply.
            try:
                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                if not isinstance(raw_content, str):
                    raise TypeError("content must be a string")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                logger.error("Groq response payload shape invalid")
                raise GroqUnavailableError(
                    "The AI returned an unexpected response. Please try again."
                ) from exc

            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                logger.error("Groq model returned non-JSON content (content omitted for privacy)")
                raise GroqUnavailableError(
                    "The AI returned an unexpected response. Please try again."
                ) from exc

            if not isinstance(parsed, dict):
                logger.error("Groq JSON content is not an object")
                raise GroqUnavailableError(
                    "The AI returned an unexpected response. Please try again."
                )
            result: dict[str, Any] = parsed

            required_keys = {"detected_tone", "applied_tone", "corrected_text", "changes_summary"}
            missing = required_keys - result.keys()
            if missing:
                logger.error("Groq response missing keys: %s", missing)
                raise GroqUnavailableError(
                    "The AI returned an incomplete response. Please try again."
                )
            return result

    # Unreachable — every code path inside the loop either returns or raises.
    raise GroqUnavailableError("Unexpected error. Please try again.")

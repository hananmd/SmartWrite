"""Pydantic schemas for the /api/correct endpoint."""

from pydantic import BaseModel, Field, field_validator

from backend.app.groq_client import VALID_TONES


class CorrectRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to correct and rewrite (1–5 000 characters).",
    )
    tone: str | None = Field(
        default=None,
        description=(
            "Target tone: 'formal', 'casual', 'friendly', or 'professional'. "
            "Omit to let the AI recommend an appropriate tone."
        ),
    )

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower()
        if v not in VALID_TONES:
            raise ValueError(
                f"tone must be one of: {', '.join(sorted(VALID_TONES))}"
            )
        return v


class CorrectResponse(BaseModel):
    corrected_text: str
    detected_tone: str
    applied_tone: str
    changes_summary: str

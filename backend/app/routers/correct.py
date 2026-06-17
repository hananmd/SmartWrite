"""Correction router: POST /api/correct (JWT-protected)."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth import get_current_user
from backend.app.groq_client import GroqUnavailableError, correct_text
from backend.app.schemas.correct import CorrectRequest, CorrectResponse

router = APIRouter(prefix="/api", tags=["correct"])


@router.post("/correct", response_model=CorrectResponse)
async def correct(
    body: CorrectRequest,
    current_user=Depends(get_current_user),
):
    """Detect tone, fix grammar, and rewrite text in the requested tone.

    Requires a valid Bearer token. Returns the corrected text plus
    the detected original tone and the tone actually applied.

    Responds 503 if Groq is down or rate-limited beyond retries so the
    caller always gets a readable error, never a raw stack trace.
    """
    try:
        result = await correct_text(body.text, body.tone)
    except GroqUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.user_message,
        )
    except ValueError as exc:
        # Catches invalid tone values that bypass the schema validator.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return CorrectResponse(**result)

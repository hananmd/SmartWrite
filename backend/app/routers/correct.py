"""Correction router: POST /api/correct (JWT-protected)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.encryption import encrypt_text
from backend.app.groq_client import GroqUnavailableError, correct_text
from backend.app.models.history import CorrectionHistory
from backend.app.schemas.correct import CorrectRequest, CorrectResponse

router = APIRouter(prefix="/api", tags=["correct"])


@router.post("/correct", response_model=CorrectResponse, status_code=status.HTTP_200_OK)
async def correct(
    body: CorrectRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect tone, fix grammar, and rewrite text in the requested tone.

    Requires a valid Bearer token. Returns the corrected text plus
    the detected original tone and the tone actually applied.

    Every correction is saved to correction_history with the text fields
    encrypted at rest (Fernet). Responds 503 if Groq is down or
    rate-limited beyond retries — the caller always gets a readable error,
    never a raw stack trace.
    """
    try:
        result = await correct_text(body.text, body.tone)
    except GroqUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.user_message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    record = CorrectionHistory(
        user_id=current_user.id,
        original_text=encrypt_text(body.text),
        corrected_text=encrypt_text(result["corrected_text"]),
        tone=result["applied_tone"],
        detected_tone=result["detected_tone"],
    )
    db.add(record)
    await db.commit()

    return CorrectResponse(**result)

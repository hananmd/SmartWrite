"""History router: GET /api/history and GET /api/analytics (JWT-protected)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.encryption import decrypt_text
from backend.app.models.history import CorrectionHistory
from backend.app.schemas.history import (
    AnalyticsResponse,
    HistoryItem,
    HistoryResponse,
    ToneCount,
)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="Records per page (1-100)."),
    offset: int = Query(default=0, ge=0, description="Number of records to skip."),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's correction history, newest first.

    Text fields are decrypted before being returned — they are only ever
    served to the owner (enforced by the JWT check + user_id filter).
    """
    # Total count for pagination metadata.
    count_result = await db.execute(
        select(func.count()).where(CorrectionHistory.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    # Fetch the requested page.
    rows_result = await db.execute(
        select(CorrectionHistory)
        .where(CorrectionHistory.user_id == current_user.id)
        .order_by(CorrectionHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = rows_result.scalars().all()

    items = [
        HistoryItem(
            id=row.id,
            original_text=decrypt_text(row.original_text),
            corrected_text=decrypt_text(row.corrected_text),
            tone=row.tone,
            detected_tone=row.detected_tone,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return HistoryResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return writing-habit analytics for the authenticated user.

    Tone and timestamp columns are stored unencrypted specifically so these
    aggregations can run without decrypting every row (see CLAUDE.md).
    """
    user_filter = CorrectionHistory.user_id == current_user.id

    # Total corrections.
    total_result = await db.execute(select(func.count()).where(user_filter))
    total = total_result.scalar_one()

    # Per-tone breakdown (tone is unencrypted — safe to GROUP BY).
    tone_rows = await db.execute(
        select(CorrectionHistory.tone, func.count().label("count"))
        .where(user_filter)
        .group_by(CorrectionHistory.tone)
        .order_by(func.count().desc())
    )
    tone_counts = [ToneCount(tone=row.tone, count=row.count) for row in tone_rows]

    most_used_tone = tone_counts[0].tone if tone_counts else None

    # Corrections in the last 7 days.
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count()).where(
            user_filter, CorrectionHistory.created_at >= seven_days_ago
        )
    )
    corrections_last_7_days = recent_result.scalar_one()

    return AnalyticsResponse(
        total_corrections=total,
        most_used_tone=most_used_tone,
        corrections_per_tone=tone_counts,
        corrections_last_7_days=corrections_last_7_days,
    )

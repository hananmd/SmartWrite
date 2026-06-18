"""Pydantic schemas for /api/history and /api/analytics."""

from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    original_text: str
    corrected_text: str
    tone: str
    detected_tone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class ToneCount(BaseModel):
    tone: str
    count: int


class AnalyticsResponse(BaseModel):
    total_corrections: int
    most_used_tone: str | None
    corrections_per_tone: list[ToneCount]
    corrections_last_7_days: int

"""CorrectionHistory ORM model.

original_text and corrected_text are stored as Fernet-encrypted bytes
(LargeBinary → BLOB/SQLite, BYTEA/Postgres). Encrypt before insert;
decrypt when serving back to the authenticated owner.

tone and detected_tone stay unencrypted — needed for analytics aggregation
(e.g. most-used tone) without decrypting every row.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class CorrectionHistory(Base):
    __tablename__ = "correction_history"
    __table_args__ = (
        # Prevent bad AI responses from silently poisoning analytics aggregations.
        CheckConstraint(
            "tone IN ('formal', 'casual', 'friendly', 'professional')",
            name="ck_correction_history_tone",
        ),
        # detected_tone allows 'neutral' — the model can detect it even though we
        # never request it as a target tone.
        CheckConstraint(
            "detected_tone IN ('formal', 'casual', 'friendly', 'professional', 'neutral')",
            name="ck_correction_history_detected_tone",
        ),
        # Composite index covers both the paginated history query (WHERE user_id ORDER BY
        # created_at DESC) and the analytics time-range filter (WHERE user_id AND created_at >=).
        Index("ix_correction_history_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Fernet-encrypted bytes — decrypt only when serving to the owner.
    original_text: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    corrected_text: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Unencrypted — used for analytics aggregation.
    tone: Mapped[str] = mapped_column(String(50), nullable=False)
    detected_tone: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

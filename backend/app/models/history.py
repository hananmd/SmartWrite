"""CorrectionHistory ORM model.

original_text and corrected_text are stored as Fernet-encrypted bytes
(LargeBinary → BLOB/SQLite, BYTEA/Postgres). Encrypt before insert;
decrypt when serving back to the authenticated owner.

tone and detected_tone stay unencrypted — needed for analytics aggregation
(e.g. most-used tone) without decrypting every row.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class CorrectionHistory(Base):
    __tablename__ = "correction_history"

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
        nullable=False,
    )

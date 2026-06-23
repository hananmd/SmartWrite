"""fix_schema_constraints

- Add server_default=CURRENT_TIMESTAMP to users.created_at and
  correction_history.created_at so raw SQL inserts don't require an
  explicit value.
- Add CHECK constraints on correction_history.tone and detected_tone to
  guard analytics aggregations against bad AI responses.
- Add composite index (user_id, created_at) on correction_history to
  serve the paginated history query and the analytics time-range filter
  without a post-filter sort.

Revision ID: f3a9b2e1d0c8
Revises: 8e3f920c1a74
Create Date: 2026-06-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a9b2e1d0c8"
down_revision: Union[str, None] = "8e3f920c1a74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )

    with op.batch_alter_table("correction_history", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.create_check_constraint(
            "ck_correction_history_tone",
            "tone IN ('formal', 'casual', 'friendly', 'professional')",
        )
        batch_op.create_check_constraint(
            "ck_correction_history_detected_tone",
            "detected_tone IN ('formal', 'casual', 'friendly', 'professional', 'neutral')",
        )
        batch_op.create_index(
            "ix_correction_history_user_created",
            ["user_id", "created_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("correction_history", schema=None) as batch_op:
        batch_op.drop_index("ix_correction_history_user_created")
        batch_op.drop_constraint("ck_correction_history_detected_tone", type_="check")
        batch_op.drop_constraint("ck_correction_history_tone", type_="check")
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )

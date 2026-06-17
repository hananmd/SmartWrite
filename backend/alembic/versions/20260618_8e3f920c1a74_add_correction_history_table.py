"""add_correction_history_table

Revision ID: 8e3f920c1a74
Revises: fc7642e3fc7a
Create Date: 2026-06-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e3f920c1a74'
down_revision: Union[str, None] = 'fc7642e3fc7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'correction_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('original_text', sa.LargeBinary(), nullable=False),
        sa.Column('corrected_text', sa.LargeBinary(), nullable=False),
        sa.Column('tone', sa.String(length=50), nullable=False),
        sa.Column('detected_tone', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('correction_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_correction_history_user_id'), ['user_id'])


def downgrade() -> None:
    with op.batch_alter_table('correction_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_correction_history_user_id'))

    op.drop_table('correction_history')

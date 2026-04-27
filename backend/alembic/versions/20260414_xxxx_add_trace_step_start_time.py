"""add_trace_step_start_time

Revision ID: 20260414xxxx
Revises: 58402ef5c44c
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260414xxxx'
down_revision: Union[str, Sequence[str], None] = '58402ef5c44c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add start_time_ms column to trace_steps table."""
    op.add_column('trace_steps', sa.Column('start_time_ms', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove start_time_ms column from trace_steps table."""
    op.drop_column('trace_steps', 'start_time_ms')

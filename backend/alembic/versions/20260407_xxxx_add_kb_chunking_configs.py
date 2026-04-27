"""add_kb_chunking_configs

Revision ID: 20260407_xxxx
Revises: bd8801e65d35
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON


# revision identifiers, used by Alembic.
revision: str = '20260407_xxxx'
down_revision: Union[str, Sequence[str], None] = 'bd8801e65d35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 kb_chunking_configs 表
    op.create_table(
        'kb_chunking_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('category_id', sa.String(), nullable=False),
        sa.Column('chunking_strategy', sa.String(), nullable=False, server_default='recursive_text'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default=sa.text('512')),
        sa.Column('overlap', sa.Integer(), nullable=False, server_default=sa.text('50')),
        sa.Column('strategy_overrides', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['kb_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id')
    )

    # 为现有分类创建默认配置
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text("""
            INSERT INTO kb_chunking_configs (id, category_id, chunking_strategy, max_tokens, overlap, created_at)
            SELECT
                lower(hex(randomblob(16))),
                id,
                'recursive_text',
                512,
                50,
                :now
            FROM kb_categories
            WHERE id IN ('default', 'translation', 'log')
        """).bindparams(now=now)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('kb_chunking_configs')

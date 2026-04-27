"""drop_sync_cron_hour

Revision ID: drop_sync_cron_hour
Revises: remove_feishu_url_unique
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'drop_sync_cron_hour'
down_revision: Union[str, Sequence[str], None] = 'remove_feishu_url_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除 feishu_documents.sync_cron_hour 冗余字段。"""
    with op.batch_alter_table('feishu_documents', schema=None) as batch_op:
        batch_op.drop_column('sync_cron_hour')


def downgrade() -> None:
    """恢复 sync_cron_hour 字段。"""
    with op.batch_alter_table('feishu_documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sync_cron_hour', sa.Integer(), nullable=True, default=-1))

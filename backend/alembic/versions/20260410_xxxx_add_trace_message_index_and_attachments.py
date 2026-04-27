"""add_trace_message_index_and_attachments

Revision ID: add_trace_message_index_and_attachments
Revises: drop_sync_cron_hour
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_trace_message_index_and_attachments'
down_revision: Union[str, Sequence[str], None] = 'drop_sync_cron_hour'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 agent_traces 表添加 message_index 和 attachments_json 字段。"""
    with op.batch_alter_table('agent_traces', schema=None) as batch_op:
        # message_index: 记录这是该 session 中的第几条 assistant 消息（0-indexed），默认为 0
        batch_op.add_column(sa.Column('message_index', sa.Integer(), nullable=False, server_default='0'))
        # attachments_json: 存储 attachments 引用的 JSON 字符串
        batch_op.add_column(sa.Column('attachments_json', sa.Text(), nullable=True))


def downgrade() -> None:
    """移除 message_index 和 attachments_json 字段。"""
    with op.batch_alter_table('agent_traces', schema=None) as batch_op:
        batch_op.drop_column('attachments_json')
        batch_op.drop_column('message_index')

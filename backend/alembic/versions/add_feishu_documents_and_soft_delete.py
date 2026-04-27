"""add_feishu_documents_and_soft_delete

Revision ID: add_feishu_documents_and_soft_delete
Revises: bd8801e65d35
Create Date: 2026-04-07

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_feishu_documents_and_soft_delete'
down_revision: Union[str, Sequence[str], None] = 'bd8801e65d35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add feishu_documents table and soft delete fields to documents."""
    # 1. 创建 feishu_documents 表
    op.create_table(
        'feishu_documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('feishu_doc_url', sa.String(), nullable=False),
        sa.Column('feishu_doc_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('kb_category_id', sa.String(), nullable=False),
        sa.Column('last_fetched_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('sync_interval_hours', sa.Integer(), nullable=True, default=24),
        sa.Column('sync_cron_hour', sa.Integer(), nullable=True, default=-1),
        sa.Column('last_sync_status', sa.String(), nullable=True, default='pending'),
        sa.Column('last_sync_error', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['kb_category_id'], ['kb_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feishu_documents_feishu_doc_url'), 'feishu_documents', ['feishu_doc_url'], unique=True)
    op.create_index(op.f('ix_feishu_documents_kb_category_id'), 'feishu_documents', ['kb_category_id'], unique=False)

    # 2. 使用 batch mode 为 documents 表添加软删除字段
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('feishu_doc_id', sa.String(), nullable=True))

    # 3. 创建 feishu_doc_id 索引
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index(op.f('ix_documents_feishu_doc_id'), ['feishu_doc_id'], unique=False)


def downgrade() -> None:
    """Remove feishu_documents table and soft delete fields from documents."""
    # 1. 删除 documents 表的索引和字段
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_documents_feishu_doc_id'))
        batch_op.drop_column('feishu_doc_id')
        batch_op.drop_column('deleted_at')

    # 2. 删除 feishu_documents 表及其索引
    op.drop_index(op.f('ix_feishu_documents_kb_category_id'), table_name='feishu_documents')
    op.drop_index(op.f('ix_feishu_documents_feishu_doc_url'), table_name='feishu_documents')
    op.drop_table('feishu_documents')

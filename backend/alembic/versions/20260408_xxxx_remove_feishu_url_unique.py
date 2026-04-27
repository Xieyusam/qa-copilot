"""remove_feishu_url_unique

Revision ID: remove_feishu_url_unique
Revises: add_feishu_documents_and_soft_delete, 20260407_xxxx
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_feishu_url_unique'
down_revision: Union[str, Sequence[str], None] = ('add_feishu_documents_and_soft_delete', '20260407_xxxx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """移除 feishu_documents.feishu_doc_url 的唯一约束，允许同一 URL 重复注册。"""
    with op.batch_alter_table('feishu_documents', schema=None) as batch_op:
        # 先删除原有的 unique index
        batch_op.drop_index('ix_feishu_documents_feishu_doc_url')
        # 重新创建为普通（非唯一）索引
        batch_op.create_index('ix_feishu_documents_feishu_doc_url', ['feishu_doc_url'], unique=False)


def downgrade() -> None:
    """恢复 feishu_documents.feishu_doc_url 的唯一约束。"""
    with op.batch_alter_table('feishu_documents', schema=None) as batch_op:
        batch_op.drop_index('ix_feishu_documents_feishu_doc_url')
        batch_op.create_index('ix_feishu_documents_feishu_doc_url', ['feishu_doc_url'], unique=True)

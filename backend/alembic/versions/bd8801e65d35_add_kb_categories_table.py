"""add_kb_categories_table

Revision ID: bd8801e65d35
Revises: 58402ef5c44c
Create Date: 2026-04-02 18:07:15.990418

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from alembic.operations import Operations


# revision identifiers, used by Alembic.
revision: str = 'bd8801e65d35'
down_revision: Union[str, Sequence[str], None] = '58402ef5c44c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 创建 kb_categories 表
    op.create_table('kb_categories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_categories_name'), 'kb_categories', ['name'], unique=True)

    # 2. 插入默认分类数据
    now = datetime.now(timezone.utc)
    op.execute(
        sa.text("""
            INSERT INTO kb_categories (id, name, description, created_at)
            VALUES
                ('default', 'default', '默认知识库，存放通用文档资料', :now),
                ('translation', 'translation', '翻译知识库，存放专业术语和翻译规范', :now),
                ('log', 'log', '日志知识库，存放系统日志和错误分析文档', :now)
        """).bindparams(now=now)
    )

    # 3. 使用 batch mode 处理 documents 表（SQLite 必须使用）
    with op.batch_alter_table('documents', schema=None) as batch_op:
        # 添加新列
        batch_op.add_column(sa.Column('kb_category_id', sa.String(), nullable=True))

        # 迁移数据需要在 batch 外执行（因为 SQLite batch mode 会复制表）
        # 所以我们在这里只添加列，数据迁移在外部执行

    # 4. 迁移数据：将旧的 kb_category 字符串值映射到新的外键
    op.execute(
        sa.text("""
            UPDATE documents
            SET kb_category_id = kb_category
            WHERE kb_category IN ('default', 'translation', 'log')
        """)
    )

    # 5. 设置默认值（处理可能的 NULL）
    op.execute(
        sa.text("UPDATE documents SET kb_category_id = 'default' WHERE kb_category_id IS NULL")
    )

    # 6. 使用 batch mode 添加外键约束并删除旧列
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_documents_kb_category', 'kb_categories', ['kb_category_id'], ['id'])
        batch_op.alter_column('kb_category_id', nullable=False)
        batch_op.drop_column('kb_category')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. 使用 batch mode 添加旧的 kb_category 列
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kb_category', sa.String(), nullable=True))

    # 2. 迁移数据回旧列
    op.execute(
        sa.text("UPDATE documents SET kb_category = kb_category_id")
    )

    # 3. 使用 batch mode 完成剩余操作
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_documents_kb_category', type_='foreignkey')
        batch_op.drop_column('kb_category_id')
        batch_op.alter_column('kb_category', nullable=False)

    # 4. 删除 kb_categories 表
    op.drop_index(op.f('ix_kb_categories_name'), table_name='kb_categories')
    op.drop_table('kb_categories')

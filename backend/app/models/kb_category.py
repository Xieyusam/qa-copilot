"""
知识库分类模型。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class KbCategory(Base):
    """知识库分类模型 - 支持用户自定义分类"""
    __tablename__ = "kb_categories"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True
    )  # 分类名称（如 qa-docs）
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )  # 分类描述
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=True
    )  # 创建者（管理员）

    # 关联文档
    documents: Mapped[list["Document"]] = relationship(
        back_populates="kb_category_rel",
        lazy="dynamic",
        cascade="all, delete-orphan"  # 删除分类时级联删除文档
    )

    # 关联飞书文档 🔜 下个版本修复，暂时禁用
    # feishu_documents: Mapped[list["FeishuDocument"]] = relationship(
    #     back_populates="kb_category_rel",
    #     lazy="dynamic"
    # )

    # 关联切分配置
    chunking_config: Mapped["KbChunkingConfig"] = relationship(
        back_populates="category",
        uselist=False,
        cascade="all, delete-orphan",
    )
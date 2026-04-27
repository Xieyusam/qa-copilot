"""
飞书文档模型 - 支持飞书文档同步管理。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class FeishuDocument(Base):
    """飞书文档同步配置模型。"""
    __tablename__ = "feishu_documents"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    feishu_doc_url: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )
    feishu_doc_type: Mapped[str] = mapped_column(
        String,
        nullable=False
    )  # "doc" | "sheet" | "bitable"
    title: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    kb_category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("kb_categories.id"),
        nullable=False
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        default=True
    )
    sync_interval_hours: Mapped[int] = mapped_column(
        Integer,
        default=24
    )
    last_sync_status: Mapped[str] = mapped_column(
        String,
        default="pending"
    )  # "pending" | "success" | "failed"
    last_sync_error: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )
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

    # 关联知识库分类 🔜 下个版本修复，暂时禁用
    # kb_category_rel: Mapped["KbCategory"] = relationship(
    #     back_populates="feishu_documents",
    #     lazy="joined"
    # )

"""
切分配置模型 - 支持按知识库分类配置不同的切分策略。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class KbChunkingConfig(Base):
    """知识库切分配置模型 - 每个分类有独立的切分配置"""
    __tablename__ = "kb_chunking_configs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    category_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("kb_categories.id"),
        unique=True,
        nullable=False
    )
    chunking_strategy: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="recursive_text"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=512
    )
    overlap: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50
    )
    strategy_overrides: Mapped[dict | None] = mapped_column(
        JSON,
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

    # 关联分类
    category: Mapped["KbCategory"] = relationship(
        back_populates="chunking_config",
        uselist=False
    )
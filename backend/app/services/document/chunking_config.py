"""
ChunkingConfigService - 切分配置读写服务。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.chunking_config import KbChunkingConfig


@dataclass
class DefaultChunkingConfig:
    """内存中的默认配置（不入库）"""
    category_id: str
    chunking_strategy: str = "recursive_text"
    max_tokens: int = 512
    overlap: int = 50
    strategy_overrides: dict | None = None

    def __post_init__(self):
        # 确保类型正确
        self.max_tokens = int(self.max_tokens)
        self.overlap = int(self.overlap)


class ChunkingConfigService:
    """切分配置读写服务"""

    def get_config(self, category_id: str) -> KbChunkingConfig | DefaultChunkingConfig:
        """
        获取分类的切分配置。

        Args:
            category_id: 分类 ID

        Returns:
            KbChunkingConfig 如果数据库中有记录
            DefaultChunkingConfig 如果没有记录（内存对象，不入库）
        """
        db = SessionLocal()
        try:
            config = db.query(KbChunkingConfig).filter(
                KbChunkingConfig.category_id == category_id
            ).first()

            if config:
                return config

            # 返回默认配置（内存对象）
            return DefaultChunkingConfig(category_id=category_id)
        finally:
            db.close()

    def upsert_config(
        self,
        category_id: str,
        strategy: str,
        max_tokens: int,
        overlap: int,
        overrides: dict | None = None,
    ) -> KbChunkingConfig:
        """
        创建或更新分类的切分配置。

        Args:
            category_id: 分类 ID
            strategy: 切分策略
            max_tokens: 最大 token 数
            overlap: 重叠 token 数
            overrides: 各文件类型的策略覆盖

        Returns:
            更新后的 KbChunkingConfig
        """
        db = SessionLocal()
        try:
            existing = db.query(KbChunkingConfig).filter(
                KbChunkingConfig.category_id == category_id
            ).first()

            if existing:
                # 更新
                existing.chunking_strategy = strategy
                existing.max_tokens = max_tokens
                existing.overlap = overlap
                existing.strategy_overrides = overrides
                existing.updated_at = datetime.now(timezone.utc)
                config = existing
            else:
                # 创建
                config = KbChunkingConfig(
                    category_id=category_id,
                    chunking_strategy=strategy,
                    max_tokens=max_tokens,
                    overlap=overlap,
                    strategy_overrides=overrides,
                )
                db.add(config)

            db.commit()
            db.refresh(config)
            return config
        finally:
            db.close()

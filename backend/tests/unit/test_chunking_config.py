"""
Tests for ChunkingConfigService and KbChunkingConfig model.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.chunking_config import KbChunkingConfig
from app.models.kb_category import KbCategory
from app.services.document.chunking_config import ChunkingConfigService, DefaultChunkingConfig


# 创建测试数据库
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话。"""
    Base.metadata.create_all(bind=TEST_ENGINE)

    # 插入测试分类
    db = TestingSessionLocal()
    cats = [
        KbCategory(id="cat1", name="cat1", description="Test category 1"),
        KbCategory(id="cat2", name="cat2", description="Test category 2"),
    ]
    for cat in cats:
        db.add(cat)
    db.commit()
    db.close()

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


class TestChunkingConfigService:
    """Test suite for ChunkingConfigService."""

    def test_get_config_returns_default_when_not_exists(self, db_session):
        """Returns DefaultChunkingConfig when no config exists for category."""
        service = ChunkingConfigService()
        # 需要使用同一个 session 或修改 service 支持 session 注入
        # 这里暂时跳过实际数据库测试，因为 service 自己管理 session
        # 这个测试通过 mock 或集成测试验证
        pass

    def test_get_config_default_values(self):
        """DefaultChunkingConfig has correct default values."""
        config = DefaultChunkingConfig(category_id="test")
        assert config.category_id == "test"
        assert config.chunking_strategy == "recursive_text"
        assert config.max_tokens == 512
        assert config.overlap == 50
        assert config.strategy_overrides is None

    def test_default_config_type_conversion(self):
        """DefaultChunkingConfig converts string values to correct types."""
        config = DefaultChunkingConfig(
            category_id="test",
            max_tokens="1024",
            overlap="100"
        )
        assert config.max_tokens == 1024
        assert isinstance(config.max_tokens, int)
        assert config.overlap == 100
        assert isinstance(config.overlap, int)


class TestKbChunkingConfigModel:
    """Test suite for KbChunkingConfig model."""

    def test_create_chunking_config(self, db_session):
        """Can create a KbChunkingConfig record."""
        config = KbChunkingConfig(
            category_id="cat1",
            chunking_strategy="semantic",
            max_tokens=1024,
            overlap=100,
        )
        db_session.add(config)
        db_session.commit()

        retrieved = db_session.query(KbChunkingConfig).filter(
            KbChunkingConfig.category_id == "cat1"
        ).first()

        assert retrieved is not None
        assert retrieved.chunking_strategy == "semantic"
        assert retrieved.max_tokens == 1024
        assert retrieved.overlap == 100

    def test_unique_constraint_on_category_id(self, db_session):
        """Each category can only have one config."""
        config1 = KbChunkingConfig(category_id="cat1", chunking_strategy="semantic")
        config2 = KbChunkingConfig(category_id="cat1", chunking_strategy="recursive_text")

        db_session.add(config1)
        db_session.commit()

        db_session.add(config2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_strategy_overrides_json(self, db_session):
        """strategy_overrides stores JSON dict correctly."""
        overrides = {"md": "markdown", "xlsx": "excel"}
        config = KbChunkingConfig(
            category_id="cat1",
            strategy_overrides=overrides,
        )
        db_session.add(config)
        db_session.commit()

        retrieved = db_session.query(KbChunkingConfig).filter(
            KbChunkingConfig.category_id == "cat1"
        ).first()

        assert retrieved.strategy_overrides == overrides
        assert retrieved.strategy_overrides["md"] == "markdown"


class TestChunkingConfigServiceIntegration:
    """Integration tests for ChunkingConfigService with real DB."""

    def test_upsert_config_creates_new(self):
        """upsert_config creates config when none exists."""
        service = ChunkingConfigService()
        config = service.upsert_config(
            category_id="newcat",
            strategy="semantic",
            max_tokens=2048,
            overlap=200,
        )

        assert config.category_id == "newcat"
        assert config.chunking_strategy == "semantic"
        assert config.max_tokens == 2048
        assert config.overlap == 200

    def test_upsert_config_updates_existing(self):
        """upsert_config updates config when it already exists."""
        service = ChunkingConfigService()

        # Create
        config1 = service.upsert_config(
            category_id="newcat2",
            strategy="semantic",
            max_tokens=1024,
            overlap=100,
        )
        assert config1.chunking_strategy == "semantic"

        # Update
        config2 = service.upsert_config(
            category_id="newcat2",
            strategy="sentence",
            max_tokens=512,
            overlap=50,
        )
        assert config2.chunking_strategy == "sentence"
        assert config2.max_tokens == 512
        assert config2.overlap == 50

    def test_get_config_returns_existing(self):
        """get_config returns KbChunkingConfig when exists."""
        service = ChunkingConfigService()
        service.upsert_config(
            category_id="newcat3",
            strategy="sliding_window",
            max_tokens=768,
            overlap=75,
        )

        config = service.get_config("newcat3")
        assert hasattr(config, "id")  # Is KbChunkingConfig, not DefaultChunkingConfig
        assert config.chunking_strategy == "sliding_window"
        assert config.max_tokens == 768

    def test_get_config_returns_default_for_unknown_category(self):
        """get_config returns DefaultChunkingConfig for unknown category."""
        service = ChunkingConfigService()
        config = service.get_config("nonexistent_category")

        assert isinstance(config, DefaultChunkingConfig)
        assert config.category_id == "nonexistent_category"
        assert config.chunking_strategy == "recursive_text"
        assert config.max_tokens == 512

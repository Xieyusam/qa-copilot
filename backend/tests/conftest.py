import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.api.dependencies import get_current_user, require_admin, get_db as dep_get_db
# categories.py 定义了自己的 get_db，需要单独 override
from app.api.categories import get_db as cat_get_db
from app.models import Base
from app.models.user import User
from app.models.kb_category import KbCategory
from app.services.llm.llm_client import LLMClient


# 创建独立测试数据库（内存 SQLite）
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话用于测试。"""
    # 每个测试函数前重建表结构
    Base.metadata.create_all(bind=TEST_ENGINE)

    # 插入默认分类（id 与实际数据库一致）
    db = TestingSessionLocal()
    default_cats = [
        KbCategory(id="default", name="default", description="默认知识库"),
        KbCategory(id="translation", name="translation", description="翻译知识库"),
        KbCategory(id="log", name="log", description="日志知识库"),
        # 添加一个有文档的分类用于关联测试
        KbCategory(id="testrel", name="test-relation", description="关联测试分类"),
    ]
    for cat in default_cats:
        db.add(cat)
    db.commit()
    db.close()

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 测试后删除表
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def override_auth():
    """覆盖认证依赖，使所有请求通过管理员身份验证。"""
    test_user = User(id="test-admin-id", username="testadmin", role="admin")

    def override_get_current_user():
        return test_user

    def override_require_admin():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_admin] = override_require_admin
    # 覆盖 categories.py 中定义的 get_db（不经过 dependencies.get_db）
    app.dependency_overrides[cat_get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_auth):
    """创建已应用认证 override 的 TestClient（供其他测试模块使用）。"""
    return TestClient(app)


@pytest.fixture
def mock_feishu_client():
    """Mock Feishu fetcher client for testing."""
    from app.services.integrations.feishu_fetcher import BaseFeishuFetcher
    return MagicMock(spec=BaseFeishuFetcher)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock = MagicMock(spec=LLMClient)
    mock.chat = AsyncMock(return_value="摘要结果")
    return mock

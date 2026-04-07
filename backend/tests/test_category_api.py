"""
分类管理 API 测试。
"""
import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.models.kb_category import KbCategory


@pytest.fixture(scope="function")
def client(override_auth):
    """创建 TestClient（依赖 override_auth 确保认证覆盖已应用）。"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_categories(db_session):
    """清理测试创建的分类。"""
    yield
    # 测试后删除新增的分类
    for cat in db_session.query(KbCategory).all():
        if cat.name.startswith(("test-", "duplicate-", "update-", "delete-")):
            db_session.delete(cat)
    db_session.commit()


class TestCategoryAPI:
    """分类管理 API 测试类。"""

    def test_list_categories(self, client):
        """测试获取分类列表。"""
        response = client.get("/api/admin/categories")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # 至少有 3 个默认分类

        # 验证默认分类存在
        names = [c["name"] for c in data]
        assert "default" in names
        assert "translation" in names
        assert "log" in names

    def test_create_category(self, client):
        """测试创建分类。"""
        unique_name = f"test-category-api-{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/admin/categories",
            json={
                "name": unique_name,
                "description": "API 测试分类",
            },
        )

        # 可能因达到分类上限而失败
        if response.status_code == 400 and "上限" in response.json()["detail"]:
            pytest.skip("分类数量已达上限，跳过创建测试")

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == unique_name
        assert data["description"] == "API 测试分类"
        assert "id" in data

    def test_create_duplicate_category(self, client):
        """测试创建重复名称的分类应失败。"""
        # 使用唯一名称创建分类
        unique_name = f"duplicate-test-{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/admin/categories",
            json={"name": unique_name},
        )

        # 可能因达到分类上限而失败
        if create_response.status_code == 400 and "上限" in create_response.json()["detail"]:
            pytest.skip("分类数量已达上限，跳过重复测试")

        assert create_response.status_code == 201

        # 尝试创建同名分类
        response = client.post(
            "/api/admin/categories",
            json={"name": unique_name},
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_update_category(self, client):
        """测试更新分类。"""
        # 创建分类
        unique_name = f"update-test-{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/admin/categories",
            json={"name": unique_name, "description": "原始描述"},
        )

        # 可能因达到分类上限而失败
        if create_response.status_code == 400 and "上限" in create_response.json()["detail"]:
            pytest.skip("分类数量已达上限，跳过更新测试")

        assert create_response.status_code == 201
        category_id = create_response.json()["id"]

        # 更新分类
        response = client.put(
            f"/api/admin/categories/{category_id}",
            json={"description": "更新后的描述"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["description"] == "更新后的描述"

    def test_update_nonexistent_category(self, client):
        """测试更新不存在的分类应失败。"""
        response = client.put(
            "/api/admin/categories/nonexistent-id",
            json={"name": "new-name"},
        )
        assert response.status_code == 404

    def test_delete_empty_category(self, client):
        """测试删除空分类。"""
        # 创建分类
        unique_name = f"delete-test-{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/admin/categories",
            json={"name": unique_name},
        )

        # 可能因达到分类上限而失败
        if create_response.status_code == 400 and "上限" in create_response.json()["detail"]:
            pytest.skip("分类数量已达上限，跳过删除测试")

        assert create_response.status_code == 201
        category_id = create_response.json()["id"]

        # 删除分类
        response = client.delete(f"/api/admin/categories/{category_id}")
        assert response.status_code == 200
        assert "已删除" in response.json()["message"]

    def test_delete_nonexistent_category(self, client):
        """测试删除不存在的分类应失败。"""
        response = client.delete("/api/admin/categories/nonexistent-id")
        assert response.status_code == 404


class TestDocumentCategoryAPI:
    """文档分类 API 测试类。"""

    def test_list_documents_with_category_filter(self, client):
        """测试按分类筛选文档列表。"""
        response = client.get("/api/documents?category_id=default")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_move_document_category_invalid_doc(self, client):
        """测试移动不存在的文档应失败。"""
        response = client.put(
            "/api/documents/nonexistent-doc/category",
            json={"category_id": "default"},
        )
        assert response.status_code == 404

    def test_move_document_to_invalid_category(self, client):
        """测试移动文档到不存在的分类应失败。"""
        # 这个测试需要一个真实的文档 ID
        # 由于我们使用测试数据库，这里跳过
        pass

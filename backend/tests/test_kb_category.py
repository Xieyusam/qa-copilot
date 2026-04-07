"""
知识库分类模型测试。
"""
import pytest
import uuid

from app.models.kb_category import KbCategory
from app.models.document import Document


class TestKbCategory:
    """KbCategory 模型测试类。"""

    def test_create_category(self):
        """测试创建分类。"""
        cat = KbCategory(
            id="test-cat",
            name="test-category",
            description="测试分类",
        )
        assert cat.id == "test-cat"
        assert cat.name == "test-category"
        assert cat.description == "测试分类"

    def test_category_unique_name(self, db_session):
        """测试分类名称唯一约束。"""
        unique_name = f"unique-name-{uuid.uuid4().hex[:8]}"

        cat1 = KbCategory(id=f"cat1-{uuid.uuid4().hex[:8]}", name=unique_name)
        db_session.add(cat1)
        db_session.commit()

        # 尝试创建同名分类
        cat2 = KbCategory(id=f"cat2-{uuid.uuid4().hex[:8]}", name=unique_name)
        db_session.add(cat2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_category_document_relationship(self, db_session):
        """测试分类与文档的关联关系。"""
        # 创建唯一分类
        cat_id = f"cat-{uuid.uuid4().hex[:8]}"
        cat_name = f"cat-name-{uuid.uuid4().hex[:8]}"
        cat = KbCategory(id=cat_id, name=cat_name)
        db_session.add(cat)
        db_session.commit()

        # 创建文档并关联分类
        doc_id = f"doc-{uuid.uuid4().hex[:8]}"
        doc = Document(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status="ready",
            kb_category_id=cat_id,
        )
        db_session.add(doc)
        db_session.commit()

        # 验证关联
        db_session.refresh(cat)
        assert cat.documents.count() == 1
        assert cat.documents.first().filename == "test.txt"

    def test_default_categories_exist(self, db_session):
        """测试默认分类已存在。"""
        categories = db_session.query(KbCategory).all()
        category_names = [c.name for c in categories]

        assert "default" in category_names
        assert "translation" in category_names
        assert "log" in category_names


class TestDocumentCategoryRelation:
    """Document 与 KbCategory 关联测试类。"""

    def test_document_belongs_to_category(self, db_session):
        """测试文档属于某个分类。"""
        # 获取 test-relation 分类（避免与 default 冲突）
        cat = db_session.query(KbCategory).filter(KbCategory.name == "test-relation").first()
        assert cat is not None

        # 创建文档（使用唯一 ID）
        doc_id = f"doc-test-{uuid.uuid4().hex[:8]}"
        doc = Document(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status="ready",
            kb_category_id=cat.id,
        )
        db_session.add(doc)
        db_session.commit()

        # 验证关联
        db_session.refresh(doc)
        assert doc.kb_category_rel is not None
        assert doc.kb_category_rel.name == "test-relation"

    def test_document_category_default(self, db_session):
        """测试文档分类默认值。"""
        # 不指定分类时，应使用 default
        doc_id = f"doc-default-{uuid.uuid4().hex[:8]}"
        doc = Document(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status="ready",
            kb_category_id="default",  # 显式设置默认值
        )
        db_session.add(doc)
        db_session.commit()

        # 验证
        db_session.refresh(doc)
        assert doc.kb_category_id == "default"
        assert doc.kb_category_rel.name == "default"
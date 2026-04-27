"""
Tests for Categories API — delete behavior.
Feature: internal-knowledge-base, fixbug-1 Problem 1
  - Cannot delete category that has documents (returns 400)
  - Can delete empty category (returns 200)
Feature: fixbug-6 Problem 4
  - Cannot delete category that has FeishuDocuments (returns 400)
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.models.kb_category import KbCategory
from app.models.document import Document
from app.models.feishu_document import FeishuDocument


class TestDeleteCategory:
    """Tests for DELETE /api/admin/categories/{id}."""

    def test_delete_category_with_documents_returns_400(self, client, db_session):
        """
        Deleting a category that still has documents must return 400
        with a Chinese error message indicating the document count.
        """
        # Create a category with a document
        cat = KbCategory(id="cat-with-docs", name="cat-with-docs")
        db_session.add(cat)
        doc = Document(
            id="doc-1",
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status="ready",
            kb_category_id="cat-with-docs",
        )
        db_session.add(doc)
        db_session.commit()

        response = client.delete("/api/admin/categories/cat-with-docs")

        assert response.status_code == 400
        assert "1" in response.json()["detail"]

    def test_delete_empty_category_succeeds(self, client, db_session):
        """Deleting a category with zero documents succeeds with 200."""
        cat = KbCategory(id="cat-empty", name="cat-empty")
        db_session.add(cat)
        db_session.commit()

        response = client.delete("/api/admin/categories/cat-empty")

        assert response.status_code == 200
        assert "已删除" in response.json()["message"]

    def test_delete_nonexistent_category_returns_404(self, client, db_session):
        """Deleting a non-existent category returns 404."""
        response = client.delete("/api/admin/categories/nonexistent")
        assert response.status_code == 404

    def test_delete_category_with_feishu_documents_returns_400(self, client, db_session):
        """
        Deleting a category that has FeishuDocuments must return 400
        with a message indicating the FeishuDocument count.
        fixbug-6 Issue #4.
        """
        # Create a category with a FeishuDocument
        cat = KbCategory(id="cat-with-feishu", name="cat-with-feishu")
        db_session.add(cat)
        feishu_doc = FeishuDocument(
            id="feishu-1",
            feishu_doc_url="https://feishu.cn/wiki/xxx",
            feishu_doc_type="doc",
            title="Test Feishu Doc",
            kb_category_id="cat-with-feishu",
            is_active=True,
            sync_interval_hours=-1,
            last_sync_status="pending",
        )
        db_session.add(feishu_doc)
        db_session.commit()

        response = client.delete("/api/admin/categories/cat-with-feishu")

        assert response.status_code == 400
        assert "飞书文档" in response.json()["detail"]
        assert "1" in response.json()["detail"]

"""
飞书文档拉取服务单元测试。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.integrations.feishu_fetcher import FeishuFetcher
from app.services.integrations.feishu_client import BaseFeishuFetcher


class MockFeishuClient(BaseFeishuFetcher):
    """模拟的飞书客户端。"""

    def __init__(self, fetch_result=None, title="Test Doc"):
        self._fetch_result = fetch_result or (b"content", "txt")
        self._title = title

    async def fetch_document(self, doc_url):
        return self._fetch_result

    async def get_document_title(self, doc_url):
        return self._title


class TestFeishuFetcherNoClient:
    """测试无客户端情况。"""

    @pytest.mark.asyncio
    async def test_upsert_raises_without_client(self):
        """没有客户端时抛出 RuntimeError。"""
        fetcher = FeishuFetcher(client=None)
        with pytest.raises(RuntimeError, match="未配置"):
            await fetcher.upsert_by_url(
                url="https://example.com/doc",
                category_id="default"
            )


class TestFeishuFetcherCleanup:
    """测试 _cleanup_document 方法。"""

    @pytest.mark.asyncio
    async def test_cleanup_calls_vector_delete(self):
        """测试清理时调用向量删除。"""
        with patch("app.services.integrations.feishu_fetcher.VectorStore") as mock_vs, \
             patch("app.services.integrations.feishu_fetcher.HybridRetriever") as mock_hr, \
             patch("app.services.integrations.feishu_fetcher.settings") as mock_settings:

            mock_vs.return_value = MagicMock()
            mock_hr.return_value = MagicMock()
            mock_settings.file_storage_path = "/tmp"

            fetcher = FeishuFetcher()
            await fetcher._cleanup_document("doc-123")

            mock_vs.return_value.delete_by_doc_id.assert_called_once_with("doc-123")
            mock_hr.return_value.remove_doc_from_bm25.assert_called_once_with("doc-123")


class TestFeishuFetcherSync:
    """测试同步方法。"""

    @pytest.mark.asyncio
    async def test_sync_updates_status_on_error(self):
        """测试同步失败时更新状态。"""
        with patch("app.services.integrations.feishu_fetcher.SessionLocal") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)

            feishu_doc = MagicMock()
            feishu_doc.id = "fd-123"
            feishu_doc.feishu_doc_url = "https://example.com/doc"
            feishu_doc.kb_category_id = "cat-1"
            feishu_doc.last_sync_status = "pending"
            mock_session.get.return_value = feishu_doc

            fetcher = FeishuFetcher(client=None)  # 无客户端会导致失败
            await fetcher.sync_document(feishu_doc)

            # 验证状态更新为 failed
            assert feishu_doc.last_sync_status == "failed"
            assert feishu_doc.last_sync_error is not None


class TestFeishuFetcherSoftDelete:
    """测试软删除方法。"""

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self):
        """测试 URL 不存在时不操作。"""
        with patch("app.services.integrations.feishu_fetcher.SessionLocal") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session.query.return_value.filter.return_value.first.return_value = None

            fetcher = FeishuFetcher()
            await fetcher.soft_delete("https://notfound.com/doc")
            assert not mock_session.commit.called

    @pytest.mark.asyncio
    async def test_soft_delete_sets_deleted_at(self):
        """测试软删除设置 deleted_at。"""
        with patch("app.services.integrations.feishu_fetcher.SessionLocal") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)

            feishu_doc = MagicMock()
            feishu_doc.id = "fd-123"
            doc1 = MagicMock()
            doc1.deleted_at = None
            doc2 = MagicMock()
            doc2.deleted_at = None

            mock_session.query.return_value.filter.return_value.first.return_value = feishu_doc
            mock_session.query.return_value.filter.return_value.all.return_value = [doc1, doc2]

            fetcher = FeishuFetcher()
            await fetcher.soft_delete("https://example.com/doc")

            assert doc1.deleted_at is not None
            assert doc2.deleted_at is not None
            assert mock_session.commit.called

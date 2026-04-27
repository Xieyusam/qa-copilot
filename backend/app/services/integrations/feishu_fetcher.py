"""
飞书文档拉取与同步服务。
"""
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from app.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.feishu_document import FeishuDocument
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.document.uploader import DocumentUploader
from app.services.retrieval.vector_store import VectorStore
from app.services.observability.logger import get_logger

if TYPE_CHECKING:
    from app.services.feishu_client import BaseFeishuFetcher

logger = get_logger(__name__)


class FeishuFetcher:
    """
    飞书文档拉取服务 - 处理飞书文档的同步与软删除逻辑。

    同步策略：更新已存在的 Document 记录（不创建新记录）
    - 注册时已创建 Document 占位记录
    - 同步时更新该记录的内容和状态
    """

    def __init__(
        self,
        client: "BaseFeishuFetcher | None" = None,
        uploader: DocumentUploader | None = None,
    ):
        self._client = client
        self._uploader = uploader or DocumentUploader()

    async def upsert_by_url(
        self,
        url: str,
        category_id: str,
        feishu_doc: FeishuDocument | None = None,
        existing_doc_id: str | None = None,
    ) -> Document | None:
        """
        根据 URL 同步飞书文档。

        如果已存在关联的 Document 记录（existing_doc_id），则更新该记录；
        否则查找旧的记录进行更新或创建新记录。

        Args:
            url: 飞书文档 URL
            category_id: 知识库分类 ID
            feishu_doc: 关联的飞书文档配置（可选）
            existing_doc_id: 已存在的 Document ID（注册时创建）

        Returns:
            Document | None: 更新后的文档对象
        """
        if self._client is None:
            raise RuntimeError("飞书 API 未配置（FEISHU_APP_ID/FEISHU_APP_SECRET 未设置），无法同步")

        db = SessionLocal()
        try:
            # 获取文档标题
            title = await self._client.get_document_title(url)
            if title is None:
                logger.warning("FeishuFetcher: could not get document title for %s", url)
                title = "Untitled"

            # 获取文档内容（根据 URL 类型自动选择拉取方式）
            result = await self._client.fetch_document_by_url(url)
            if result is None:
                logger.warning("FeishuFetcher: could not fetch document %s", url)
                return None

            file_content, file_ext = result
            filename = f"{title}.{file_ext}" if file_ext else title

            # 查找要更新的 Document 记录
            doc = None
            if existing_doc_id:
                doc = db.get(Document, existing_doc_id)

            if not doc and feishu_doc:
                # 通过 feishu_doc_id 查找已存在的记录
                doc = db.query(Document).filter(
                    Document.feishu_doc_id == feishu_doc.id,
                    Document.deleted_at.is_(None),
                ).first()

            if doc:
                # 更新现有 Document 记录
                logger.info("FeishuFetcher: updating existing document %s", doc.id)

                # 删除旧的文件和向量数据
                await self._cleanup_document(doc.id)

                # 更新字段
                doc.filename = filename
                doc.file_type = file_ext or "unknown"
                doc.file_size = len(file_content)
                doc.status = "processing"
                doc.processed_at = None
                doc.error_msg = None
            else:
                # 这种情况不应该发生，因为注册时已创建占位记录
                logger.warning("FeishuFetcher: no existing document found, creating new one")
                import uuid
                doc_id = str(uuid.uuid4())
                doc = Document(
                    id=doc_id,
                    filename=filename,
                    file_type=file_ext or "unknown",
                    file_size=len(file_content),
                    status="processing",
                    kb_category_id=category_id,
                    feishu_doc_id=feishu_doc.id if feishu_doc else None,
                )
                db.add(doc)

            db.commit()
            db.refresh(doc)

            # 保存文件
            dest_dir = self._uploader._get_dest_dir(doc.id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / filename

            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(file_content)

            # 验证文件保存成功
            if not dest_path.exists():
                doc.status = "failed"
                doc.error_msg = "File save failed - file not found after write"
                db.commit()
                return None

            # 处理文档（分片、嵌入）- 会抛出异常如果失败
            await self._uploader.process_document(doc.id)

            return doc

        except Exception as exc:
            logger.exception("FeishuFetcher: failed to upsert document %s: %s", url, exc)
            return None
        finally:
            db.close()

    async def _cleanup_document(self, doc_id: str) -> None:
        """清理文档的向量数据和文件。"""
        try:
            vector_store = VectorStore()
            hybrid_retriever = HybridRetriever(embedder=None, vector_store=vector_store)

            # 删除向量数据
            vector_store.delete_by_doc_id(doc_id)
            logger.info("FeishuFetcher: deleted vectors for doc_id=%s", doc_id)

            # 删除 BM25 数据
            hybrid_retriever.remove_doc_from_bm25(doc_id)
            logger.info("FeishuFetcher: removed from BM25 for doc_id=%s", doc_id)

            # 删除文件
            dest_dir = Path(settings.file_storage_path) / doc_id
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
                logger.info("FeishuFetcher: deleted files for doc_id=%s", doc_id)
        except Exception as e:
            logger.warning("FeishuFetcher: failed to cleanup doc_id=%s: %s", doc_id, e)

    async def soft_delete(self, url: str) -> None:
        """
        软删除与给定 URL 关联的文档。

        Args:
            url: 飞书文档 URL
        """
        db = SessionLocal()
        try:
            # 通过 feishu_doc_url 查找飞书文档配置
            feishu_doc = db.query(FeishuDocument).filter(
                FeishuDocument.feishu_doc_url == url
            ).first()

            if feishu_doc is None:
                logger.warning("FeishuFetcher: no feishu document found for URL %s", url)
                return

            # 软删除关联的文档
            docs = db.query(Document).filter(
                Document.feishu_doc_id == feishu_doc.id,
                Document.deleted_at.is_(None),
            ).all()

            now = datetime.now(timezone.utc)
            for doc in docs:
                doc.deleted_at = now

            db.commit()
            logger.info("FeishuFetcher: soft deleted %d documents for URL %s", len(docs), url)
        finally:
            db.close()

    async def sync_document(self, feishu_doc: FeishuDocument, existing_doc_id: str | None = None) -> None:
        """
        同步单个飞书文档。

        Args:
            feishu_doc: 飞书文档配置对象
            existing_doc_id: 已存在的 Document ID（注册时创建）
        """
        db = SessionLocal()
        try:
            # 更新同步状态为 pending
            feishu_doc.last_sync_status = "pending"
            feishu_doc.updated_at = datetime.now(timezone.utc)
            db.commit()

            try:
                # 执行 upsert（更新已存在的 Document 记录）
                # 如果处理失败，upsert_by_url 会抛出异常返回 None
                doc = await self.upsert_by_url(
                    url=feishu_doc.feishu_doc_url,
                    category_id=feishu_doc.kb_category_id,
                    feishu_doc=feishu_doc,
                    existing_doc_id=existing_doc_id,
                )

                if doc is None:
                    raise RuntimeError("Failed to upsert document - check logs for details")

                # 验证 Document 处理状态（doc 已在 upsert_by_url 中提交，检查其 status）
                # 注意：不要用 db.refresh(doc)，因为 doc 属于 upsert_by_url 的 session
                if doc.status == "failed":
                    raise RuntimeError(f"Document processing failed: {doc.error_msg}")

                # 更新同步状态为成功
                feishu_doc.last_sync_status = "success"
                feishu_doc.last_sync_error = None
                feishu_doc.last_fetched_at = datetime.now(timezone.utc)
                logger.info("FeishuFetcher: sync completed for document %s", feishu_doc.id)

            except Exception as exc:
                # 更新同步状态为失败
                feishu_doc.last_sync_status = "failed"
                feishu_doc.last_sync_error = str(exc)
                logger.exception("FeishuFetcher: sync failed for document %s", feishu_doc.id)

                # 同时更新 Document 状态（如果存在）
                if existing_doc_id:
                    doc = db.get(Document, existing_doc_id)
                    if doc and doc.status != "failed":
                        doc.status = "failed"
                        doc.error_msg = str(exc)
            finally:
                db.commit()
        finally:
            db.close()

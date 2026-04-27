"""
飞书文档同步调度器 - 仅支持手动触发同步。
"""
import asyncio
from typing import TYPE_CHECKING

from app.models.feishu_document import FeishuDocument
from app.services.observability.logger import get_logger

if TYPE_CHECKING:
    from app.services.feishu_fetcher import FeishuFetcher

logger = get_logger(__name__)

# 模块级单例，供 feishu.py 等直接访问
_scheduler: "FeishuScheduler | None" = None


def get_scheduler() -> "FeishuScheduler | None":
    return _scheduler


def set_scheduler(sched: "FeishuScheduler") -> None:
    global _scheduler
    _scheduler = sched


class FeishuScheduler:
    """
    飞书文档同步调度器 - 仅支持手动触发同步。

    定时同步功能已移除，改为用户手动触发。
    """

    def __init__(self, fetcher: "FeishuFetcher"):
        self._fetcher = fetcher

    def trigger_sync_now(self, feishu_doc_id: str, existing_doc_id: str | None = None) -> None:
        """
        立即触发一次同步。

        Args:
            feishu_doc_id: 飞书文档 ID
            existing_doc_id: 已存在的 Document ID（可选）
        """
        logger.info("FeishuScheduler: triggering sync for document %s", feishu_doc_id)
        asyncio.create_task(self._sync_wrapper(feishu_doc_id, existing_doc_id))

    async def _sync_wrapper(self, feishu_doc_id: str, existing_doc_id: str | None = None) -> None:
        """
        同步任务的包装函数。

        Args:
            feishu_doc_id: 飞书文档 ID
        """
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            feishu_doc = db.get(FeishuDocument, feishu_doc_id)
            if feishu_doc is None:
                logger.warning(
                    "FeishuScheduler: document %s not found, skipping sync",
                    feishu_doc_id,
                )
                return

            if not feishu_doc.is_active:
                logger.info(
                    "FeishuScheduler: document %s is inactive, skipping sync",
                    feishu_doc_id,
                )
                return

            await self._fetcher.sync_document(feishu_doc, existing_doc_id=existing_doc_id)
            logger.info("FeishuScheduler: completed sync for document %s", feishu_doc_id)
        except Exception as exc:
            logger.exception(
                "FeishuScheduler: error syncing document %s: %s",
                feishu_doc_id,
                exc,
            )
        finally:
            db.close()

    def start(self) -> None:
        """启动调度器（保留接口兼容，无实际操作）。"""
        logger.info("FeishuScheduler: ready (manual sync only)")

    def shutdown(self) -> None:
        """关闭调度器（保留接口兼容，无实际操作）。"""
        logger.info("FeishuScheduler: shutdown")

"""KB 检索工具 - 绑定到特定知识库"""
from typing import Type, Optional, Any, List
from dataclasses import dataclass

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """检索结果块"""
    doc_id: str
    filename: str
    chunk_position: int
    content: str
    score: float


class KbRetrieverInput(BaseModel):
    """KB 检索工具输入 schema"""
    query: str = Field(description="检索查询")


class KbRetrieverTool(BaseTool):
    """知识库检索工具 - 绑定到特定 KB

    注意：为支持 LangGraph 序列化，不存储 retriever 实例，
    而是在调用时根据 category_name 动态创建并过滤。
    """

    name: str = ""  # 工具名称，如 "kb_云测平台"
    description: str = ""  # 工具描述
    category_id: str = ""  # KB 分类 ID，用于过滤（UUID）

    args_schema: Type[BaseModel] = KbRetrieverInput

    def _get_retriever(self):
        """动态创建 HybridRetriever（避免序列化问题）"""
        from app.services.retrieval.hybrid_retriever import HybridRetriever
        return HybridRetriever()

    def _run(self, query: str) -> str:
        """同步执行检索（不应直接调用，请使用 _arun）"""
        raise NotImplementedError("请使用 _arun 异步方法")

    async def _arun(self, query: str) -> str:
        """异步执行检索"""
        try:
            retriever = self._get_retriever()
            # 按 category_name 过滤，只检索该 KB 的文档
            chunks = await retriever.retrieve(
                query,
                top_k=5,
                filter={"kb_category_id": self.category_id}
            )
            # 格式化结果
            formatted = self._format_chunks(chunks)
            # 将 chunks 信息存储在 self 上，供 SearchWorker 提取
            self._last_chunks = [
                RetrievedChunk(
                    doc_id=getattr(c, 'doc_id', ''),
                    filename=getattr(c, 'filename', '未知文件'),
                    chunk_position=getattr(c, 'chunk_position', 0),
                    content=getattr(c, 'content', ''),
                    score=getattr(c, 'score', 0.0),
                )
                for c in chunks
            ]
            return formatted
        except Exception as e:
            logger.error(f"KbRetrieverTool {self.name} 检索失败: {e}")
            return f"检索失败: {str(e)}"

    def _format_chunks(self, chunks: list) -> str:
        """格式化检索结果"""
        if not chunks:
            return "没有找到相关文档"

        return "\n\n".join([
            f"【{getattr(c, 'filename', '未知文件')}】(相似度:{getattr(c, 'score', 0):.2f})\n{getattr(c, 'content', '')}"
            for c in chunks
        ])

"""Summarize Worker - 摘要 Worker"""
from typing import Optional

from app.services.agents.types import AgentResult
from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class SummarizeWorker(WorkerAgent):
    """Summarize Worker - 摘要专家"""

    def __init__(self, llm, trace_callback=None):
        super().__init__(name="summarize", llm=llm, trace_callback=trace_callback)

    @property
    def system_prompt(self) -> str:
        return """你是一个文本摘要专家。

你的职责：
1. 对提供的文本进行摘要
2. 提取关键信息和要点
3. 生成简洁、准确的摘要

回答规范：
- 摘要长度适中（原文的 1/3 到 1/5）
- 包含所有关键信息
- 使用清晰的结构（分点或段落）"""

    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        **kwargs
    ) -> AgentResult:
        """执行摘要"""
        try:
            # 从 context 获取待摘要文本
            text_to_summarize = kwargs.get("text") or (context.get("text") if context else None) or query

            prompt = f"""为以下文本生成摘要：

{text_to_summarize}

要求：
1. 提取关键信息
2. 简洁准确
3. 结构清晰"""

            answer = await self.llm.chat([{"role": "user", "content": prompt}])

            return AgentResult(
                type="summarize",
                answer=answer,
                sources=[],
            )

        except Exception as e:
            logger.error(f"SummarizeWorker 执行失败: {e}")
            raise

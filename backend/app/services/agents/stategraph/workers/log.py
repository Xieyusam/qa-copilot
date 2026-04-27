"""Log Worker - 日志分析 Worker"""
from typing import Optional

from app.services.agents.types import AgentResult
from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class LogWorker(WorkerAgent):
    """Log Worker - 日志分析专家"""

    def __init__(self, llm, trace_callback=None):
        super().__init__(name="log", llm=llm, trace_callback=trace_callback)

    @property
    def system_prompt(self) -> str:
        return """你是一个日志分析专家。

你的职责：
1. 分析日志内容，提取关键信息
2. 识别错误、异常、警告等
3. 提供问题诊断建议

回答规范：
- 结构清晰，使用分点和列表
- 错误信息使用代码格式
- 提供问题根因分析和建议"""

    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        **kwargs
    ) -> AgentResult:
        """执行日志分析"""
        try:
            # 日志查询逻辑
            # 这里需要根据实际日志服务实现
            prompt = f"""分析以下日志内容：

{query}

请：
1. 识别错误和异常
2. 分析问题原因
3. 提供解决建议"""

            answer = await self.llm.chat([{"role": "user", "content": prompt}])

            return AgentResult(
                type="log",
                answer=answer,
                sources=[],
            )

        except Exception as e:
            logger.error(f"LogWorker 执行失败: {e}")
            raise

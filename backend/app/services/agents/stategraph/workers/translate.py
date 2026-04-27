"""Translate Worker - 翻译专家"""
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.agents.types import AgentResult
from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.observability.logger import get_logger

logger = get_logger(__name__)

TRANSLATE_PROMPT_TEMPLATE = """你是一个翻译专家。

你有多个翻译知识库工具可以使用：
{tool_descriptions}

你的职责：
1. 根据待翻译文本，选择相关的翻译知识库获取术语参考
2. 将文本准确翻译成目标语言
3. 保持原文的专业术语和格式

支持的语言方向：中文 ↔ 英文

回答规范：
- 只输出翻译结果，不要解释
- 保持原文格式（换行、列表等）
- 术语尽量使用知识库中的标准翻译

【串行意图链】如果你是意图链的后续 Agent：
- 从 context.results 获取前一个 Agent 的结果（待翻译文本）
- 直接翻译前一个结果中的内容
"""


class TranslateWorker(WorkerAgent):
    """Translate Worker - 翻译专家"""

    def __init__(self, llm, kb_tool_registry=None, trace_callback=None):
        super().__init__(name="translate", llm=llm, trace_callback=trace_callback)
        self._kb_registry = kb_tool_registry
        self._tools = kb_tool_registry.get_translate_tools() if kb_tool_registry else []

    @property
    def tools(self):
        """返回翻译 KB 工具列表，供 bind_tools 使用"""
        return self._tools

    @property
    def system_prompt(self) -> str:
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}" for t in self._tools
        ]) or "（无可用翻译知识库）"
        return TRANSLATE_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)

    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        **kwargs
    ) -> AgentResult:
        """执行翻译"""
        try:
            # 从 context 获取待翻译文本（串行意图链）
            text_to_translate = context.get("previous_result") if context else None

            if not text_to_translate:
                text_to_translate = kwargs.get("text") or query

            target_lang = kwargs.get("target_lang", "英文")

            # 直接翻译，不使用 bind_tools（避免重复调用工具）
            prompt = f"""将以下文本翻译成{target_lang}：

{text_to_translate}

只返回翻译结果，不要其他内容。"""

            answer = await self.llm.chat([{"role": "user", "content": prompt}])

            return AgentResult(type="translate", answer=answer, sources=[])

        except Exception as e:
            logger.error(f"TranslateWorker 执行失败: {e}")
            return AgentResult(
                type="translate",
                answer=f"翻译失败: {str(e)}",
                sources=[],
            )

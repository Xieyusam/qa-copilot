"""Worker Agent 基类 - 所有 Worker Agent 的基类"""
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.agents.types import AgentResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class WorkerAgent(ABC):
    """
    Worker Agent 基类

    所有专业 Agent（search、jira、log 等）都继承此类。
    每个 Worker Agent 有自己的：
    - prompt: 系统提示词
    - 执行逻辑
    """

    def __init__(self, name: str, llm, trace_callback=None):
        """
        Args:
            name: Agent 名称（search, jira, log 等）
            llm: LLM 客户端
            trace_callback: trace 回调函数
        """
        self.name = name
        self.llm = llm
        self.trace_callback = trace_callback

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """返回系统提示词"""
        pass

    async def execute(
        self,
        query: str,
        context: Optional[dict] = None,
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        **kwargs
    ) -> AgentResult:
        """
        执行 Agent 任务

        Args:
            query: 用户查询
            context: 上下文（如前一个 Agent 的结果）
            streaming_callback: 可选的流式回调，用于实时推送 LLM tokens
            **kwargs: 其他参数

        Returns:
            AgentResult: 执行结果
        """
        import time
        start_time = time.time()

        try:
            # 记录 trace
            self._record_trace("start", query, context)

            # 执行子类逻辑（传入 streaming_callback）
            result = await self._execute_impl(query, context, streaming_callback=streaming_callback, **kwargs)

            # 记录 trace
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("end", query, result, elapsed_ms)

            return result

        except Exception as e:
            logger.error(f"{self.name} agent 执行失败: {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("error", query, str(e), elapsed_ms)

            return AgentResult(
                type=self.name,
                answer=f"[{self.name} 执行失败: {str(e)}]",
                sources=[],
            )

    @abstractmethod
    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        streaming_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        **kwargs
    ) -> AgentResult:
        """
        子类实现的执行逻辑

        Args:
            query: 用户查询
            context: 上下文
            streaming_callback: 可选的流式回调，用于实时推送 LLM tokens
            **kwargs: 其他参数

        Returns:
            AgentResult
        """
        pass

    def _record_trace(
        self,
        step: str,
        input_data: str,
        output_data: any = None,
        time_ms: float = 0
    ):
        """记录 trace"""
        if self.trace_callback:
            self.trace_callback(
                step_type=f"{self.name}_{step}",
                tool_name=self.name,
                input_prompt=str(input_data)[:500],
                output_result=str(output_data)[:500] if output_data else None,
                time_ms=time_ms,
            )

    def _build_messages(
        self,
        query: str,
        context: Optional[dict] = None,
        extra_system: str = ""
    ) -> list:
        """
        构建消息列表

        Args:
            query: 用户查询
            context: 上下文
            extra_system: 额外的系统提示

        Returns:
            消息列表
        """
        messages = []

        # 系统消息
        system_content = self.system_prompt
        if extra_system:
            system_content += f"\n\n{extra_system}"

        messages.append(SystemMessage(content=system_content))

        # 上下文
        if context:
            context_text = "\n".join([
                f"【{k}】: {v}"
                for k, v in context.items() if v
            ])
            messages.append(HumanMessage(content=f"上下文信息：\n{context_text}"))

        # 用户查询
        messages.append(HumanMessage(content=query))

        return messages

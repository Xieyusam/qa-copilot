"""Supervisor Agent - 中央协调者"""
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


SUPERVISOR_PROMPT = """你是一个任务协调者。

你的职责：
1. 分析用户意图，决定调用哪个 Worker Agent
2. 协调多个 Agent 的执行
3. 汇总结果，生成最终回答

可用 Worker Agent：
- search: 知识库检索
- jira: JIRA 查询
- log: 日志分析
- translate: 翻译
- summarize: 总结

决策规则：
1. 如果用户想要检索知识库内容 → search
2. 如果用户提到 jira、bug、issue、epic、sprint 等 → jira
3. 如果用户想要分析日志 → log
4. 如果用户要求翻译 → translate
5. 如果用户要求总结、摘要 → summarize
6. 如果所有 Agent 都执行完了 → aggregate（汇总）

当前状态：
- 用户输入：{user_input}
- 已执行结果：{existing_results}
- 待执行 Agent：{pending_agents}

请决定下一步：
- 返回 Worker 名称（search/jira/log/translate/summarize）
- 或返回 "aggregate" 表示汇总
- 或返回 "supervisor" 表示继续思考

只返回一个词，不要其他内容。"""


class SupervisorAgent:
    """
    Supervisor Agent - 中央协调者

    负责任务分配和结果汇总
    """

    def __init__(self, llm, intent_detector, trace_callback=None):
        self.llm = llm
        self.intent_detector = intent_detector
        self.trace_callback = trace_callback

    async def decide(
        self,
        user_input: str,
        existing_results: dict,
        pending_agents: list[str],
    ) -> str:
        """
        决定下一步

        Args:
            user_input: 用户输入
            existing_results: 已执行的结果
            pending_agents: 待执行的 Agent 列表

        Returns:
            下一个节点名称
        """
        import time
        start_time = time.time()

        try:
            # 如果有待执行列表，直接返回第一个
            if pending_agents:
                next_agent = pending_agents[0]
                elapsed_ms = (time.time() - start_time) * 1000
                self._record_trace("decide", user_input, next_agent, elapsed_ms)
                logger.info(f"Supervisor 决定: {next_agent} (从待执行列表)")
                return next_agent

            # 使用 intent_detector 分析意图
            intents = await self.intent_detector.detect_multi_intent(user_input)

            # 映射到 Agent 类型
            agent_map = {
                "search": "search",
                "jira": "jira",
                "log": "log",
                "translate": "translate",
                "summarize": "summarize",
            }

            # 返回第一个未执行的意图
            for intent in intents:
                agent = agent_map.get(intent)
                if agent:
                    elapsed_ms = (time.time() - start_time) * 1000
                    self._record_trace("decide", user_input, agent, elapsed_ms)
                    logger.info(f"Supervisor 决定: {agent} (从意图检测)")
                    return agent

            # 默认返回 aggregate
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("decide", user_input, "aggregate", elapsed_ms)
            return "aggregate"

        except Exception as e:
            logger.error(f"Supervisor 决策失败: {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("decide", user_input, str(e), elapsed_ms)
            return "aggregate"

    async def aggregate(self, user_input: str, results: dict) -> str:
        """
        汇总结果，生成最终回答

        Args:
            user_input: 用户输入
            results: 所有 Agent 的执行结果

        Returns:
            最终回答
        """
        import time
        start_time = time.time()

        try:
            # 构建结果摘要
            results_text = self._format_results(results)

            prompt = f"""汇总以下 Agent 的执行结果，生成最终回答。

用户问题：{user_input}

Agent 执行结果：
{results_text}

请生成最终回答：
1. 结构清晰
2. 包含所有 Agent 的关键信息
3. 简洁明了"""

            answer = await self.llm.chat([{"role": "user", "content": prompt}])

            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("aggregate", user_input, answer, elapsed_ms)

            return answer

        except Exception as e:
            logger.error(f"Supervisor 汇总失败: {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            self._record_trace("aggregate", user_input, str(e), elapsed_ms)
            return f"[汇总失败: {str(e)}]"

    def _format_results(self, results: dict) -> str:
        """格式化结果"""
        if not results:
            return "暂无执行结果"

        lines = []
        for name, result in results.items():
            if hasattr(result, "answer"):
                lines.append(f"【{name}】: {result.answer}")
            else:
                lines.append(f"【{name}】: {result}")

        return "\n".join(lines)

    def _record_trace(
        self,
        step: str,
        input_data: str,
        output_data: any,
        time_ms: float
    ):
        """记录 trace"""
        if self.trace_callback:
            self.trace_callback(
                step_type=f"supervisor_{step}",
                tool_name="supervisor",
                input_prompt=str(input_data)[:500],
                output_result=str(output_data)[:500] if output_data else None,
                time_ms=time_ms,
            )

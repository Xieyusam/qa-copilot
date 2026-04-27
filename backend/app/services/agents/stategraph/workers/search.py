"""Search Worker - 知识库检索专家"""
from typing import Optional, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import SourceRef
from app.services.agents.types import AgentResult
from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.observability.logger import get_logger

logger = get_logger(__name__)

SEARCH_PROMPT_TEMPLATE = """你是一个知识库搜索专家。

你有多个知识库工具可以使用，每个工具对应一个知识库：
{tool_descriptions}

你的职责：
1. 根据用户 query 决定查哪些知识库
2. 可以同时查多个相关知识库以获得更全面的答案
3. 基于检索结果生成准确、简洁的回答

决策规则：
- 如果 query 提到具体 KB 名称，只查那个 KB
- 如果 query 是通用问题，查所有相关 KB
- 最多同时查 3 个 KB

回答规范：
- 只回答与知识库内容相关的问题
- 如需引用，注明来源文件
- 不知道的信息如实说明

【串行意图链】如果你是意图链的第二个或后续 Agent：
- 从 context.results 获取前一个 Agent 的结果
- 如果前一个结果已包含完整回答，直接使用，无需重复检索
"""


class SearchWorker(WorkerAgent):
    """Search Worker - 知识库检索专家"""

    def __init__(self, llm, kb_tool_registry=None, trace_callback=None):
        super().__init__(name="search", llm=llm, trace_callback=trace_callback)
        self._kb_registry = kb_tool_registry
        self._tools = kb_tool_registry.get_search_tools() if kb_tool_registry else []

    @property
    def tools(self):
        """返回 KB 工具列表，供 bind_tools 使用"""
        return self._tools

    @property
    def system_prompt(self) -> str:
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}" for t in self._tools
        ]) or "（无可用知识库）"
        return SEARCH_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)

    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        streaming_callback: Optional[callable] = None,
        **kwargs
    ) -> AgentResult:
        """执行知识库检索（支持流式输出）"""
        try:
            # 检查是否是串行意图链的后续 Agent
            intent_chain = context.get("intent_chain", []) if context else []
            results = context.get("results", {}) if context else {}

            # 如果是串行链且前一个结果已存在，直接使用（避免重复检索）
            if len(intent_chain) > 1 and results:
                idx = intent_chain.index("search") if "search" in intent_chain else -1
                if idx > 0:
                    prev_agent = intent_chain[idx - 1]
                    prev_result = results.get(prev_agent)
                    if prev_result and hasattr(prev_result, "answer"):
                        logger.info(f"SearchAgent: 串行链复用前一个结果 from {prev_agent}")
                        return AgentResult(
                            type="search",
                            answer=prev_result.answer,
                            sources=getattr(prev_result, "sources", []),
                        )

            # 如果没有可用工具，返回错误
            if not self._tools:
                return AgentResult(
                    type="search",
                    answer="没有可用的知识库工具",
                    sources=[],
                )

            # 构造工具描述
            tool_descriptions = "\n".join([
                f"- {t.name}: {t.description}" for t in self._tools
            ])

            # 使用 bind_tools 让 LLM 选择 KB
            llm_with_tools = self.llm.bind_tools(self._tools)
            messages = [
                SystemMessage(content=SEARCH_PROMPT_TEMPLATE.format(tool_descriptions=tool_descriptions)),
                HumanMessage(content=f"用户问题：{query}")
            ]

            response = await llm_with_tools.ainvoke(messages)

            # 执行被调用的工具并收集来源
            tool_results = {}
            all_sources: List[SourceRef] = []
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    # 支持两种格式：ToolCall 对象或 dict
                    tc_name = tool_call.name if hasattr(tool_call, 'name') else tool_call.get('name')
                    tc_args = tool_call.arguments if hasattr(tool_call, 'arguments') else tool_call.get('args', {})
                    tool = next((t for t in self._tools if t.name == tc_name), None)
                    if tool:
                        # arun 期望 tool_input 作为位置参数
                        if isinstance(tc_args, dict):
                            tool_input = tc_args.get("query", "")
                        else:
                            tool_input = tc_args
                        result = await tool.arun(tool_input)
                        tool_results[tc_name] = result
                        logger.info(f"SearchAgent: 调用工具 {tc_name}")

                        # 从 tool 的 _last_chunks 提取来源
                        if hasattr(tool, '_last_chunks') and tool._last_chunks:
                            for chunk in tool._last_chunks:
                                source = SourceRef(
                                    doc_id=chunk.doc_id,
                                    filename=chunk.filename,
                                    chunk_position=chunk.chunk_position,
                                    content=chunk.content[:500],  # 保留部分内容用于显示
                                    similarity_score=chunk.score,
                                )
                                all_sources.append(source)
                            logger.info(f"SearchAgent: 从 {tc_name} 提取 {len(tool._last_chunks)} 个来源")

            context_text = "\n\n".join(tool_results.values()) or "没有找到相关文档"

            # 生成回答（支持流式）
            if streaming_callback:
                # 流式生成回答
                full_response = ""
                prompt = f"基于以下检索结果生成回答。\n\n检索结果：\n{context_text}\n\n用户问题：{query}"

                async for token in self.llm.astream([
                    {"role": "system", "content": "你是一个知识库搜索助手，基于检索结果生成简洁、准确的回答。如需引用，请注明来源。"},
                    {"role": "user", "content": prompt}
                ]):
                    if hasattr(token, 'content') and token.content:
                        full_response += token.content
                        await streaming_callback(token.content)

                answer = full_response
            else:
                # 普通方式生成回答
                answer = await self.llm.chat([
                    {"role": "system", "content": "基于以下检索结果生成回答。"},
                    {"role": "user", "content": f"检索结果：\n{context_text}\n\n用户问题：{query}"}
                ])

            logger.info(f"SearchAgent: 检索完成，收集到 {len(all_sources)} 个来源")
            return AgentResult(type="search", answer=answer, sources=all_sources)

        except Exception as e:
            logger.error(f"SearchWorker 执行失败: {e}")
            return AgentResult(
                type="search",
                answer=f"搜索失败: {str(e)}",
                sources=[],
            )

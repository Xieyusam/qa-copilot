"""
QA Copilot 服务：基于 LangGraph 的多意图检索增强生成流程。
"""
from __future__ import annotations

import logging
import time
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from app.core.schemas import SourceRef
from app.services.conversation import ConversationManager
from app.services.llm_client import LLMClient
from app.services.hybrid_retriever import HybridRetriever
from app.services.jira_client import JiraClient
from app.services.tool_generator import ToolGenerator, build_jira_tools
from app.services.copilot_prompts import build_system_prompt
from app.db.session import SessionLocal
from app.models.trace import AgentTrace, TraceStep
from app.models.kb_category import KbCategory

logger = logging.getLogger(__name__)


class CopilotService:
    """编排多意图检索与生成的 Copilot 服务（ReAct 架构）。"""

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        conversation_manager: ConversationManager | None = None,
        llm_client: LLMClient | None = None,
        jira_client: JiraClient | None = None,
    ) -> None:
        self._retriever = retriever or HybridRetriever()
        self._conv = conversation_manager or ConversationManager()
        self._llm_client = llm_client or LLMClient()
        self._jira_client = jira_client or JiraClient()
        self._agent = None  # 延迟构建，使用动态工具

    def _build_agent(self) -> Any:
        """构建 ReAct Agent（动态工具和提示词）。"""
        db = SessionLocal()
        try:
            # 获取所有分类
            categories = db.query(KbCategory).all()

            # 动态生成检索工具
            tool_generator = ToolGenerator(self._retriever)
            tools = tool_generator.build_retrieve_tools(db)

            # 添加 Jira 工具
            tools.extend(build_jira_tools(self._jira_client))

            # 动态生成系统提示词
            prompt = build_system_prompt(categories)

            return create_react_agent(self._llm_client.model, tools, prompt=prompt)
        finally:
            db.close()

    async def answer(self, session_id: str, question: str) -> AsyncGenerator[str, None]:
        """处理用户问题并流式返回回答。"""
        # 延迟构建 Agent（确保使用最新的分类数据）
        if self._agent is None:
            self._agent = self._build_agent()

        # 创建追踪记录
        db = SessionLocal()
        trace = AgentTrace(
            session_id=session_id,
            question=question,
            total_time_ms=0.0,
        )
        db.add(trace)
        db.commit()
        db.refresh(trace)
        trace_id = trace.id
        db.close()

        trace_start_time = time.perf_counter()
        step_index = 0

        # 获取对话历史
        history = self._conv.get_recent_history(session_id, n=10)
        messages = []
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        # 添加当前问题
        messages.append(HumanMessage(content=question))

        # 流式处理 Agent 事件
        async_stream = self._agent.astream_events(
            {"messages": messages},
            version="v2"
        )

        full_response = []
        sources_list = []
        sources = []  # 在 try 块外初始化，确保 finally 可访问

        try:
            async for event in async_stream:
                kind = event["event"]

                # LLM 流式输出
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and isinstance(chunk.content, str):
                        content = chunk.content
                        if content:
                            full_response.append(content)
                            yield content

                    # 记录 LLM 步骤（仅首次）
                    if step_index == 0:
                        step_time_ms = (time.perf_counter() - trace_start_time) * 1000
                        self._record_step(trace_id, step_index, "llm_start", None, question, step_time_ms)
                        step_index += 1

                # 工具调用结束
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    tool_name = event.get("name", "unknown_tool")

                    # 获取工具输入
                    tool_input = ""
                    if "data" in event and "input" in event["data"]:
                        tool_input = str(event["data"]["input"])

                    # 记录工具调用步骤
                    step_time_ms = (time.perf_counter() - trace_start_time) * 1000
                    output_str = str(output)[:500] if output else ""
                    self._record_step(trace_id, step_index, "tool_call", tool_name, tool_input, step_time_ms, output_str)
                    step_index += 1

                    # 收集来源信息
                    if hasattr(output, "artifact") and isinstance(output.artifact, list):
                        sources_list.extend(output.artifact)

            assistant_text = "".join(full_response)
            total_time_ms = (time.perf_counter() - trace_start_time) * 1000

            # 更新追踪记录
            self._update_trace(trace_id, assistant_text, total_time_ms)

            # 构建来源列表 - 仅包含必要字段
            sources_data = []
            seen_chunks = set()
            for src in sources_list:
                # 跳过缺少必要字段的数据（如 Jira 结果没有 doc_id）
                if not isinstance(src, dict):
                    continue
                if not all(k in src for k in ["doc_id", "filename", "position", "score", "content"]):
                    continue
                chunk_id = f"{src['doc_id']}_{src['position']}"
                if chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    sources.append(SourceRef(
                        doc_id=src["doc_id"],
                        filename=src["filename"],
                        chunk_position=src["position"],
                        similarity_score=src["score"],
                        content=src["content"],
                    ))
                    sources_data.append({
                        "doc_id": src["doc_id"],
                        "filename": src["filename"],
                        "chunk_position": src["position"],
                        "similarity_score": src["score"],
                        "content": src["content"],
                    })

            # 保存消息到会话
            self._conv.add_message(session_id, "user", question)
            self._conv.add_message(session_id, "assistant", assistant_text, sources=sources)

            if sources_data:
                yield {
                    "type": "sources",
                    "data": sources_data,
                }

        except Exception as exc:
            logger.exception("Agent 流式处理出错")
            total_time_ms = (time.perf_counter() - trace_start_time) * 1000
            self._update_trace(trace_id, f"Error: {exc}", total_time_ms)
            assistant_text = "".join(full_response) + f"\n\n[系统错误: {exc}]"
            yield f"\n\n[系统错误: {exc}]"
            # 错误情况下也保存消息，避免用户困惑
            self._conv.add_message(session_id, "user", question)
            self._conv.add_message(session_id, "assistant", assistant_text, sources=sources)

    def _record_step(self, trace_id: str, step_index: int, step_type: str,
                     tool_name: str | None, input_prompt: str | None,
                     time_ms: float, output_result: str | None = None) -> None:
        """记录单个执行步骤到追踪表。"""
        db = SessionLocal()
        try:
            step = TraceStep(
                trace_id=trace_id,
                step_index=step_index,
                step_type=step_type,
                tool_name=tool_name,
                input_prompt=input_prompt[:1000] if input_prompt else None,
                output_result=output_result[:2000] if output_result else None,
                time_ms=time_ms,
            )
            db.add(step)
            db.commit()
        except Exception as e:
            logger.error(f"记录追踪步骤失败: {e}")
        finally:
            db.close()

    def _update_trace(self, trace_id: str, final_answer: str, total_time_ms: float) -> None:
        """更新追踪记录的最终答案和耗时。"""
        db = SessionLocal()
        try:
            trace = db.get(AgentTrace, trace_id)
            if trace:
                trace.final_answer = final_answer[:5000] if final_answer else None
                trace.total_time_ms = total_time_ms
                db.commit()
        except Exception as e:
            logger.error(f"更新追踪记录失败: {e}")
        finally:
            db.close()
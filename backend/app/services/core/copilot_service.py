"""
QA Copilot 服务：基于 LangGraph StateGraph 的多 Agent 架构。
支持并行多意图、顺序复合意图、完整的执行追踪和断点恢复。
使用 astream() 实现流式输出。
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Union

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from pydantic import BaseModel, Field

from app.core.schemas import SourceRef
from app.services.core.conversation import ConversationManager
from app.services.llm.llm_client import LLMClient
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.integrations.jira_client import JiraClient
from app.services.observability.logger import get_logger
from app.services.observability.metrics import increment_counter, observe_histogram
from app.services.agents.intent_detector import IntentDetector
from app.services.agents.kb_tool_registry import KbToolRegistry
from app.services.agents.stategraph.graph import build_agent_graph, plan_and_build_initial_state
from app.services.agents.stategraph.workers.search import SearchWorker
from app.services.agents.stategraph.workers.jira import JiraWorker
from app.services.agents.stategraph.workers.log import LogWorker
from app.services.agents.stategraph.workers.translate import TranslateWorker
from app.db.session import SessionLocal
from app.models.trace import AgentTrace, TraceStep

logger = get_logger(__name__)


def _load_attachment_content(file_id: str, filename: str) -> str:
    """根据 attachment_id 读取文件内容。"""
    from pathlib import Path
    from app.config import settings
    from app.services.document.parser import DocumentParser

    attachments_dir = Path(settings.attachments_dir)
    filepath = None
    for p in attachments_dir.glob(f"{file_id}_*"):
        filepath = p
        break

    if not filepath or not filepath.exists():
        return f"[文件不存在: {filename}]"

    ext = filepath.suffix.lower().lstrip(".")
    try:
        if ext in ("pdf", "docx", "xlsx", "xls"):
            parsed = DocumentParser().parse(str(filepath), ext, doc_id=None)
            return parsed.content[:8000]
        else:
            return filepath.read_text(encoding="utf-8")[:8000]
    except Exception as e:
        return f"[解析失败: {str(e)}]"


class AttachmentMiddleware(AgentMiddleware):
    """在模型调用前注入附件内容。"""

    def wrap_model_call(self, request: ModelRequest, handler):
        new_messages = []
        for msg in request.messages:
            if hasattr(msg, "additional_kwargs") and msg.additional_kwargs.get("attachments"):
                new_messages.append(msg)
                for att in msg.additional_kwargs["attachments"]:
                    content = _load_attachment_content(att["id"], att["filename"])
                    helper = {
                        "role": "user",
                        "content": f"【附件: {att['filename']} ({att.get('size', 0)} bytes)】\n{content}"
                    }
                    new_messages.append(helper)
            else:
                new_messages.append(msg)

        new_request = request.override(messages=new_messages)
        return handler(new_request)

    async def awrap_model_call(self, request: ModelRequest, handler):
        new_messages = []
        for msg in request.messages:
            if hasattr(msg, "additional_kwargs") and msg.additional_kwargs.get("attachments"):
                new_messages.append(msg)
                for att in msg.additional_kwargs["attachments"]:
                    content = _load_attachment_content(att["id"], att["filename"])
                    helper = {
                        "role": "user",
                        "content": f"【附件: {att['filename']} ({att.get('size', 0)} bytes)】\n{content}"
                    }
                    new_messages.append(helper)
            else:
                new_messages.append(msg)

        new_request = request.override(messages=new_messages)
        return await handler(new_request)


class CopilotService:
    """
    基于 LangGraph StateGraph 的多 Agent 服务。

    使用 Supervisor-Worker 模式：
    - Supervisor: 协调任务分配
    - Workers: Search, Jira, Log, Translate 等专业 Agent
    """

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        conversation_manager: ConversationManager | None = None,
        llm_client: LLMClient | None = None,
        jira_client: JiraClient | None = None,
    ) -> None:
        self._conv = conversation_manager or ConversationManager()
        self._llm_client = llm_client or LLMClient()
        self._jira_client = jira_client or JiraClient()

        # KB 工具注册表
        self._kb_registry = KbToolRegistry()

        # 初始化 IntentDetector
        self._intent_detector = IntentDetector(self._llm_client)

        # 初始化 Workers（传入 kb_registry）
        self._search_worker = SearchWorker(
            llm=self._llm_client,
            kb_tool_registry=self._kb_registry,
        )
        self._jira_worker = JiraWorker(
            llm=self._llm_client,
            jira_client=self._jira_client,
        )
        self._log_worker = LogWorker(
            llm=self._llm_client,
        )
        self._translate_worker = TranslateWorker(
            llm=self._llm_client,
            kb_tool_registry=self._kb_registry,
        )

        # 构建图 (V2 - MAS-plan 方案)
        self._graph = build_agent_graph(
            intent_detector=self._intent_detector,
            search_worker=self._search_worker,
            jira_worker=self._jira_worker,
            log_worker=self._log_worker,
            translate_worker=self._translate_worker,
        )

        # trace 相关
        self._trace_id = None
        self._trace_callback = None

    async def answer(
        self,
        session_id: str,
        question: str,
        attachments: list[dict] | None = None,
    ) -> AsyncGenerator[Union[str, dict], None]:
        """处理用户问题并流式返回回答。

        使用 astream() 流式输出每个节点的实时状态：
        - status: 当前执行状态（如"正在搜索..."）
        - token: LLM 输出的 token 流
        - source: 知识库来源信息
        - done: 执行完成
        """
        # 获取对话历史
        history = self._conv.get_recent_history(session_id, n=10)

        # 创建追踪记录
        db = SessionLocal()
        message_index = len([m for m in history if m.role == "assistant"])
        import json
        attachments_json = json.dumps(attachments, ensure_ascii=False) if attachments else None
        logger.info(f"[copilot_service] answer called with question: {question[:50]}...")

        trace = AgentTrace(
            session_id=session_id,
            message_index=message_index,
            question=question,
            total_time_ms=0.0,
            attachments_json=attachments_json,
        )
        db.add(trace)
        db.commit()
        db.refresh(trace)
        trace_id = trace.id
        db.close()

        trace_start_time = time.perf_counter()

        # 创建 trace 回调函数
        step_index = 0
        def trace_callback(step_type: str, tool_name: str, input_prompt: str | None, output_result: str | None, time_ms: float = 0):
            nonlocal step_index
            elapsed_ms = (time.perf_counter() - trace_start_time) * 1000
            start_ms = elapsed_ms - time_ms if time_ms > 0 else elapsed_ms
            self._record_step(trace_id, step_index, step_type, tool_name, input_prompt, start_ms, elapsed_ms, output_result)
            step_index += 1

        # 设置 trace 回调
        self._search_worker.trace_callback = trace_callback
        self._jira_worker.trace_callback = trace_callback
        self._log_worker.trace_callback = trace_callback
        self._translate_worker.trace_callback = trace_callback

        # 创建 workers 字典
        workers = {
            "search": self._search_worker,
            "jira": self._jira_worker,
            "log": self._log_worker,
            "translate": self._translate_worker,
        }

        full_answer = ""
        final_state = None
        sources = []
        last_status = ""  # 用于去重的状态

        try:
            # ========== 1. 首次规划：意图检测 ==========
            yield {
                "type": "status",
                "content": "正在分析问题..."
            }

            initial_state, planned_tasks = await plan_and_build_initial_state(
                user_input=question,
                intent_detector=self._intent_detector,
                workers=workers,
                trace_id=trace_id,
                trace_callback=trace_callback,
            )

            # 根据任务类型发送状态
            task_names = {
                "search": "知识库搜索",
                "jira": "JIRA查询",
                "log": "日志分析",
                "translate": "翻译",
                "summarize": "总结",
            }
            task_types = [t["type"] for t in planned_tasks]

            # 发送初始状态
            if len(task_types) > 1 and all(t in ["search", "jira"] for t in task_types):
                last_status = f"正在并行执行{', '.join(task_names.get(t, t) for t in task_types)}..."
                yield {
                    "type": "status",
                    "content": last_status
                }
            elif len(task_types) == 1:
                last_status = f"正在执行{task_names.get(task_types[0], task_types[0])}..."
                yield {
                    "type": "status",
                    "content": last_status
                }
            else:
                last_status = "正在执行任务..."
                yield {
                    "type": "status",
                    "content": last_status
                }

            # ========== 2. 使用 astream_events() 获取细粒度事件流 ==========
            # astream_events 提供最丰富的事件类型，包括：
            # - on_chat_model_stream: LLM token 流（来自 bind_tools，非答案内容，不推送）
            # - on_chain_start/end: 节点开始/结束
            # 注意：由于 bind_tools 的 token 与答案内容无关，不进行流式推送以避免重复
            try:
                async for event in self._graph.astream_events(initial_state, version="v2"):
                    kind = event.get("event", "")
                    node_name = event.get("metadata", {}).get("langgraph_node", "N/A")

                    if kind == "on_chain_start" and node_name:
                        # 节点开始执行
                        if node_name not in ("search", "jira", "log", "translate", "summarize"):
                            continue
                        streaming = f"正在执行{node_name}..."
                        if streaming != last_status:
                            last_status = streaming
                            yield {
                                "type": "status",
                                "content": streaming
                            }

                    elif kind == "on_chain_end":
                        # 节点执行完成 - 收集来源（从所有节点的 results 中）
                        outputs = event.get("data", {}).get("output", {})
                        if isinstance(outputs, dict):
                            results_list = outputs.get("results", [])
                            # 收集来源（去重）
                            seen_keys = {(s.doc_id, s.chunk_position) for s in sources}
                            for r in results_list:
                                if hasattr(r, "sources") and r.sources:
                                    for s in r.sources:
                                        if (s.doc_id, s.chunk_position) not in seen_keys:
                                            sources.append(s)
                                            seen_keys.add((s.doc_id, s.chunk_position))

                        if node_name == "aggregate":
                            # aggregate 节点完成，处理最终输出
                            if isinstance(outputs, dict):
                                final_output = outputs.get("final_output", "")
                                if final_output and len(final_output) > len(full_answer):
                                    full_answer = final_output

            except Exception as stream_error:
                logger.warning(f"astream_events 执行异常: {stream_error}")
                import traceback
                traceback.print_exc()

                # 降级使用 ainvoke
                try:
                    final_state = await self._graph.ainvoke(initial_state)
                    if final_state:
                        full_answer = final_state.get("final_output", "") or ""
                        if full_answer:
                            yield {
                                "type": "token",
                                "content": full_answer
                            }
                        for result in final_state.get("results", []):
                            if hasattr(result, "sources") and result.sources:
                                sources.extend(result.sources)
                except Exception as invoke_error:
                    logger.error(f"ainvoke 降级也失败: {invoke_error}")

            total_time_ms = (time.perf_counter() - trace_start_time) * 1000

            # ========== 3.5 发送完整的 final_output（aggregate 节点结果）==========
            if full_answer:
                yield {
                    "type": "token",
                    "content": full_answer
                }

            # ========== 4. 完成信号 ==========
            yield {
                "type": "done",
                "content": "执行完成"
            }

            # 更新追踪记录
            self._update_trace(trace_id, full_answer, total_time_ms)

            # 保存消息到会话
            user_kwargs = {"attachments": attachments} if attachments else None
            self._conv.add_message(session_id, "user", question, additional_kwargs=user_kwargs)
            self._conv.add_message(session_id, "assistant", full_answer, sources=sources)

            # 发送来源给前端
            if sources:
                yield {
                    "type": "sources",
                    "data": [
                        {
                            "docId": src.doc_id,
                            "filename": src.filename,
                            "chunkPosition": src.chunk_position,
                            "similarityScore": src.similarity_score,
                            "content": src.content,
                        }
                        for src in sources
                    ],
                }

        except Exception as exc:
            logger.exception("多 Agent 执行出错")
            total_time_ms = (time.perf_counter() - trace_start_time) * 1000
            self._update_trace(trace_id, f"Error: {exc}", total_time_ms)
            yield {
                "type": "error",
                "content": str(exc)
            }
            # 错误情况下也保存消息
            user_kwargs = {"attachments": attachments} if attachments else None
            self._conv.add_message(session_id, "user", question, additional_kwargs=user_kwargs)
            self._conv.add_message(session_id, "assistant", f"Error: {exc}", sources=[])

    def _record_step(self, trace_id: str, step_index: int, step_type: str,
                     tool_name: str | None, input_prompt: str | None,
                     start_ms: float, end_ms: float,
                     output_result: str | None = None) -> None:
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
                start_time_ms=start_ms,
                time_ms=end_ms,
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

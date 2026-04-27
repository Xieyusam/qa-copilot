"""Summarize 节点 - 从 State 读取 (MAS-plan 方案)

兼容 Send 调用和普通调用两种方式
"""
from typing import Dict, Any

from app.services.agents.stategraph.state import OverallState, TaskResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def summarize_node(state: Any) -> Dict:
    """
    Summarize 节点 - 执行摘要
    """
    # 兼容 Send 调用：提取 workers
    workers = state.get("workers", {}) if isinstance(state, dict) else state.get("workers", {})

    if not workers:
        if hasattr(state, "get"):
            raise ValueError("summarize_worker not found in state.workers")
        raise ValueError("summarize_worker not found")

    summarize_worker = workers.get("summarize")
    if not summarize_worker:
        raise ValueError("summarize_worker not found in state.workers")

    # 从 planned_tasks 获取当前任务的 query
    planned_tasks = state.get("planned_tasks", [])
    query = None
    for task in planned_tasks:
        if task["type"] == "summarize":
            query = task.get("query", "")
            break

    # 从 state.results 获取前一个任务的结果
    results = state.get("results", [])
    text_to_summarize = None

    for r in reversed(results):
        if r.agent_type != "summarize":
            text_to_summarize = r.answer
            break

    if not text_to_summarize:
        text_to_summarize = state.get("user_input", "")

    logger.info(f"summarize_node: 待摘要文本长度={len(text_to_summarize)}")

    # 执行摘要
    result = await summarize_worker.execute(
        query=query or text_to_summarize,
        context={}
    )

    # 记录 trace
    trace_callback = state.get("trace_callback") if isinstance(state, dict) else getattr(state, "get", lambda x: None)("trace_callback")
    if trace_callback:
        trace_callback(
            step_type="summarize",
            tool_name="summarize",
            input_prompt=text_to_summarize[:500],
            output_result=result.answer[:500] if result.answer else None,
            time_ms=0,
        )

    # 创建 TaskResult 并返回
    task_result = TaskResult(
        agent_type="summarize",
        answer=result.answer,
        sources=getattr(result, "sources", []),
    )

    return {
        "results": [task_result],
        "streaming_output": "总结完成",
    }

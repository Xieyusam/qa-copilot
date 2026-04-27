"""Translate 节点 - 从 State 读取 (MAS-plan 方案)

兼容 Send 调用和普通调用两种方式
核心改进：从 state.results 读取前一个结果并翻译
"""
from typing import Dict, Any

from app.services.agents.stategraph.state import OverallState, TaskResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def translate_node(state: Any) -> Dict:
    """
    Translate 节点 - 执行翻译
    """
    # 兼容 Send 调用：提取 workers
    workers = state.get("workers", {}) if isinstance(state, dict) else state.get("workers", {})

    if not workers:
        if hasattr(state, "get"):
            raise ValueError("translate_worker not found in state.workers")
        raise ValueError("translate_worker not found")

    translate_worker = workers.get("translate")
    if not translate_worker:
        raise ValueError("translate_worker not found in state.workers")

    # 从 planned_tasks 获取当前任务的 query
    planned_tasks = state.get("planned_tasks", [])
    query = None
    for task in planned_tasks:
        if task["type"] == "translate":
            query = task.get("query", "翻译成英文")
            break

    # 从 state.results 获取前一个任务的结果
    results = state.get("results", [])
    text_to_translate = None

    for r in reversed(results):
        if r.agent_type != "translate":
            text_to_translate = r.answer
            break

    if not text_to_translate:
        text_to_translate = state.get("user_input", "")

    logger.info(f"translate_node: 待翻译文本长度={len(text_to_translate)}")

    # 执行翻译
    result = await translate_worker.execute(
        query=query or "翻译成英文",
        context={"previous_result": text_to_translate}
    )

    # 记录 trace
    trace_callback = state.get("trace_callback") if isinstance(state, dict) else getattr(state, "get", lambda x: None)("trace_callback")
    if trace_callback:
        trace_callback(
            step_type="translate",
            tool_name="translate",
            input_prompt=text_to_translate[:500],
            output_result=result.answer[:500] if result.answer else None,
            time_ms=0,
        )

    # 创建 TaskResult 并返回
    task_result = TaskResult(
        agent_type="translate",
        answer=result.answer,
        sources=getattr(result, "sources", []),
    )

    return {
        "results": [task_result],
        "streaming_output": "翻译完成",
    }

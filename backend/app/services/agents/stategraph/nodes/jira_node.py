"""Jira 节点 - 从 State 读取 (MAS-plan 方案)

兼容 Send 调用和普通调用两种方式
"""
from typing import Dict, Any

from app.services.agents.stategraph.state import OverallState, TaskResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def jira_node(state: Any) -> Dict:
    """
    Jira 节点 - 执行 JIRA 查询
    """
    # 兼容 Send 调用：提取 workers
    workers = state.get("workers", {}) if isinstance(state, dict) else state.get("workers", {})

    if not workers:
        if hasattr(state, "get"):
            raise ValueError("jira_worker not found in state.workers")
        raise ValueError("jira_worker not found")

    jira_worker = workers.get("jira")
    if not jira_worker:
        raise ValueError("jira_worker not found in state.workers")

    # 从 planned_tasks 获取当前任务的 query
    planned_tasks = state.get("planned_tasks", [])
    query = None
    for task in planned_tasks:
        if task["type"] == "jira":
            query = task.get("query", "")
            break

    if not query:
        query = state.get("user_input", "")

    logger.info(f"jira_node: 执行 JIRA 查询 query={query[:50]}...")

    # 执行查询
    result = await jira_worker.execute(query=query, context={})

    # 记录 trace
    trace_callback = state.get("trace_callback") if isinstance(state, dict) else getattr(state, "get", lambda x: None)("trace_callback")
    if trace_callback:
        trace_callback(
            step_type="jira",
            tool_name="jira",
            input_prompt=query[:500],
            output_result=result.answer[:500] if result.answer else None,
            time_ms=0,
        )

    # 创建 TaskResult 并返回
    task_result = TaskResult(
        agent_type="jira",
        answer=result.answer,
        sources=getattr(result, "sources", []),
    )

    return {
        "results": [task_result],
        "streaming_output": "JIRA查询完成",
    }

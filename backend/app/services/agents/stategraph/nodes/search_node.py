"""Search 节点 - 从 State 读取 (MAS-plan 方案)

核心改进：
1. 从 state 直接读取 query（由 supervisor 规划）
2. 从 state.results 读取前一个结果（用于串行链）
3. 返回 TaskResult 对象到 results list（通过 Annotated[list, add] 合并）
"""
from typing import Dict, Any
from langgraph.types import Command

from app.services.agents.stategraph.state import OverallState, TaskResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def search_node(state: Any) -> Dict:
    """
    Search 节点 - 执行知识库检索

    兼容两种调用方式：
    1. 普通调用：接收完整 OverallState
    2. Send 调用：接收 {"planned_tasks": [...], "results": [...]} 字典
    """
    # 兼容 Send 调用：提取 workers
    workers = state.get("workers", {}) if isinstance(state, dict) else state.get("workers", {})

    if not workers:
        # 如果 state 是 OverallState 但没有 workers，说明出错了
        if hasattr(state, "get"):
            raise ValueError("search_worker not found in state.workers")
        raise ValueError("search_worker not found")

    search_worker = workers.get("search")
    if not search_worker:
        raise ValueError("search_worker not found in state.workers")

    # 从 planned_tasks 获取当前任务的 query
    planned_tasks = state.get("planned_tasks", [])
    query = None
    for task in planned_tasks:
        if task["type"] == "search":
            query = task.get("query", "")
            break

    if not query:
        query = state.get("user_input", "")

    # 检查是否是串行链：从 results 获取前一个结果
    context = {}
    results = state.get("results", [])
    if results:
        # 找到前一个任务的结果
        for r in reversed(results):
            if r.agent_type in ["translate", "summarize"]:
                continue
            context["previous_result"] = r.answer
            break

    logger.info(f"search_node: 执行搜索 query={query[:50]}...")

    # 执行搜索
    result = await search_worker.execute(query=query, context=context)

    # 记录 trace
    trace_callback = state.get("trace_callback") if isinstance(state, dict) else getattr(state, "get", lambda x: None)("trace_callback")
    if trace_callback:
        trace_callback(
            step_type="search",
            tool_name="search",
            input_prompt=query[:500],
            output_result=result.answer[:500] if result.answer else None,
            time_ms=0,
        )

    # 创建 TaskResult
    task_result = TaskResult(
        agent_type="search",
        answer=result.answer,
        sources=getattr(result, "sources", []),
    )

    # 返回结果，框架会自动合并到主状态
    # 边的目标是 supervisor，所以执行完后会回到 supervisor
    return {
        "results": [task_result],
        "streaming_output": "知识库搜索完成",
    }

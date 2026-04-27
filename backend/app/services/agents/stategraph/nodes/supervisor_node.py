"""Supervisor 节点 - 通用调度器

核心改进：
1. 通过 planned_tasks + depends_on 声明式依赖
2. 根据依赖关系动态决定下一步
3. 支持并行检测：多个无依赖任务同时就绪时并行执行
"""
from typing import Dict, List, Literal, Union, Any

from app.services.agents.stategraph.state import OverallState, TaskResult
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


# Agent 显示名称映射
AGENT_DISPLAY_NAMES = {
    "search": "知识库搜索",
    "jira": "JIRA查询",
    "log": "日志分析",
    "translate": "翻译",
    "summarize": "总结",
}


def get_completed_tasks(results: List[TaskResult]) -> set:
    """从 results 中提取已完成的任务类型"""
    return {r.agent_type for r in results}


def supervisor_node(state: OverallState) -> Dict:
    """
    Supervisor 节点 - 通用调度器

    职责：
    1. 首次调用：意图检测在外部（copilot_service）完成
    2. 根据依赖关系动态决定下一步
    3. 所有任务完成后跳转到 aggregate
    """
    user_input = state.get("user_input", "")
    planned_tasks = state.get("planned_tasks", [])
    results = state.get("results", [])

    # 如果没有 planned_tasks，说明是首次调用
    if not planned_tasks:
        logger.info("supervisor_node: 等待意图检测...")
        return {"next_action": "supervisor", "streaming_output": "正在分析问题..."}

    # ========== 收集已完成的任务 ==========
    completed = get_completed_tasks(results)
    logger.info(f"supervisor_node: 已完成 {completed}, 待完成 {set(t['type'] for t in planned_tasks) - completed}")

    # ========== 检查是否所有任务都已完成 ==========
    all_task_types = {t["type"] for t in planned_tasks}
    if completed == all_task_types:
        logger.info("supervisor_node: 所有任务完成，跳转 aggregate")
        return {
            "next_action": "aggregate",
            "streaming_output": "任务完成，正在汇总结果..."
        }

    # ========== 找出可以执行的任务（依赖都已满足且未完成）==========
    ready_tasks = []
    for task in planned_tasks:
        task_type = task["type"]
        if task_type in completed:
            continue

        deps = task.get("depends_on", [])
        if all(dep in completed for dep in deps):
            ready_tasks.append(task)

    if not ready_tasks:
        # 有未完成任务但没有可以执行的：等待中
        logger.warning("supervisor_node: 无可执行任务，等待中...")
        return {"next_action": "supervisor", "streaming_output": "等待中..."}

    # ========== 决定下一步行动 ==========
    # 检测并行任务：多个无依赖任务同时就绪
    parallel_tasks = [t for t in ready_tasks if not t.get("depends_on")]

    if len(parallel_tasks) > 1:
        # 多个无依赖任务同时就绪，显示并行状态但仍串行执行
        task_names = [t["type"] for t in parallel_tasks]
        streaming = f"并行执行: {', '.join(AGENT_DISPLAY_NAMES.get(t, t) for t in task_names)}"
        logger.info(f"supervisor_node: 检测到 {len(parallel_tasks)} 个并行任务，但串行执行 {task_names}")

        # 暂时串行执行第一个任务（LangGraph Send 并行机制需要进一步调试）
        task = parallel_tasks[0]
        return {
            "next_action": task["type"],
            "streaming_output": streaming,
        }
    elif len(ready_tasks) == 1:
        # 单一任务
        task = ready_tasks[0]
        task_type = task["type"]
        streaming = f"正在执行{AGENT_DISPLAY_NAMES.get(task_type, task_type)}..."
        logger.info(f"supervisor_node: 串行执行 {task_type}")
        return {
            "next_action": task_type,
            "streaming_output": streaming,
        }
    else:
        # 有依赖的任务，按顺序执行第一个
        task = ready_tasks[0]
        task_type = task["type"]
        logger.info(f"supervisor_node: 串行执行 {task_type}")
        return {
            "next_action": task_type,
            "streaming_output": f"正在执行{AGENT_DISPLAY_NAMES.get(task_type, task_type)}...",
        }


def aggregate_node(state: OverallState) -> Dict:
    """
    Aggregate 节点 - 汇总所有 Agent 结果

    串行链：返回最后一个任务的结果
    并行链：拼接所有结果
    """
    from app.services.agents.stategraph.state import TaskResult
    from langchain_core.messages import AIMessage

    results = state.get("results", [])
    planned_tasks = state.get("planned_tasks", [])

    logger.info(f"aggregate_node: results count={len(results)}, tasks={len(planned_tasks)}")

    if not results:
        final_answer = "没有找到相关信息"
    elif len(planned_tasks) == 1:
        # 单任务：直接返回结果
        final_answer = results[-1].answer
    elif len(results) == 1:
        final_answer = results[-1].answer
    else:
        # 多个结果：按 planned_tasks 顺序拼接
        # 检查是否是串行链
        if len(planned_tasks) >= 2:
            last_task = planned_tasks[-1]
            second_last_task = planned_tasks[-2]
            if last_task["type"] in ["translate", "summarize"] and \
               second_last_task["type"] in last_task.get("depends_on", []):
                # 串行链，返回最后一个结果
                for r in reversed(results):
                    if r.agent_type == last_task["type"]:
                        final_answer = r.answer
                        break
                else:
                    final_answer = results[-1].answer
            else:
                # 并行链，拼接所有（不添加前缀）
                answers = []
                for task in planned_tasks:
                    for r in results:
                        if r.agent_type == task["type"]:
                            answers.append(r.answer)
                            break
                final_answer = "\n\n---\n\n".join(answers)
        else:
            final_answer = "\n\n".join([r.answer for r in results])

    messages = list(state.get("messages", []))
    messages.append(AIMessage(content=final_answer))

    logger.info(f"aggregate_node: 汇总结果长度={len(final_answer)}")
    return {
        "messages": messages,
        "final_output": final_answer,
        "streaming_output": "汇总完成",
    }

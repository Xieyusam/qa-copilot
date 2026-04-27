"""LangGraph StateGraph 构建和编译 (MAS-plan 方案)

核心改进：
1. 使用 OverallState 替代 AgentState
2. results 使用 Annotated[list, operator.add] 自动合并并行结果
3. 使用 Command 和 Send 进行动态路由
4. supervisor 返回 Command 或 List[Send]
"""
from typing import Dict, List, Literal, Union, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Send

from app.services.agents.stategraph.state import OverallState
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


def _passthrough_router(state: OverallState) -> Any:
    """
    透传路由函数 - 读取 next_action 并返回对应节点

    支持的 next_action 值：
    - "supervisor": 继续等待
    - "aggregate": 跳转到汇总节点
    - "search/jira/log/translate/summarize": 跳转到对应worker
    - "parallel": 需要特殊处理（暂时不支持）
    """
    next_action = state.get("next_action", "aggregate")

    # 如果是 parallel，暂时用第一个任务（后续需要实现真正的并行）
    if next_action == "parallel":
        parallel_tasks = state.get("parallel_tasks", [])
        if parallel_tasks:
            # 取第一个任务执行（简化实现）
            next_action = parallel_tasks[0]["type"]
        else:
            next_action = "supervisor"

    return next_action


def build_agent_graph(
    intent_detector,
    search_worker,
    jira_worker,
    log_worker,
    translate_worker=None,
    summarize_worker=None,
    trace_callback=None,
) -> StateGraph:
    """构建 Agent 执行图 (MAS-plan Command/Send 方案)"""

    # 创建 workers 字典
    workers = {
        "search": search_worker,
        "jira": jira_worker,
        "log": log_worker,
        "translate": translate_worker,
        "summarize": summarize_worker,
    }

    # 延迟导入避免循环依赖
    from app.services.agents.stategraph.nodes.supervisor_node import supervisor_node, aggregate_node
    from app.services.agents.stategraph.nodes.search_node import search_node
    from app.services.agents.stategraph.nodes.jira_node import jira_node
    from app.services.agents.stategraph.nodes.log_node import log_node
    from app.services.agents.stategraph.nodes.translate_node import translate_node
    from app.services.agents.stategraph.nodes.summarize_node import summarize_node

    builder = StateGraph(OverallState)

    # 添加节点
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("search", search_node)
    builder.add_node("jira", jira_node)
    builder.add_node("log", log_node)
    builder.add_node("aggregate", aggregate_node)

    # 可选节点
    if translate_worker:
        builder.add_node("translate", translate_node)
    if summarize_worker:
        builder.add_node("summarize", summarize_node)

    # 设置入口点
    builder.set_entry_point("supervisor")

    # ========== MAS-plan Command/Send 路由设计 ==========
    #
    # Workers 执行完后通过 edges 回到 supervisor
    # supervisor 返回 Command(goto="next") 或 List[Send] 来动态调度

    # Workers 完成后回到 supervisor
    builder.add_edge("search", "supervisor")
    builder.add_edge("jira", "supervisor")
    builder.add_edge("log", "supervisor")
    if translate_worker:
        builder.add_edge("translate", "supervisor")
    if summarize_worker:
        builder.add_edge("summarize", "supervisor")

    # 条件边：使用 _passthrough_router 透传 supervisor 的 Command/Send
    # 注意：LangGraph 的 conditional_edges 需要一个 router 函数，
    # 这里返回 None 表示不改变路由，继续等待
    # 只包含实际添加的节点
    routes = {
        "aggregate": "aggregate",
        "supervisor": "supervisor",
        "search": "search",
        "jira": "jira",
        "log": "log",
    }
    if translate_worker:
        routes["translate"] = "translate"
    if summarize_worker:
        routes["summarize"] = "summarize"

    builder.add_conditional_edges(
        "supervisor",
        _passthrough_router,
        routes
    )

    # Aggregate 后结束
    builder.add_edge("aggregate", END)

    # 编译图
    graph = builder.compile()

    # 挂载属性
    graph.intent_detector = intent_detector
    graph.trace_callback = trace_callback
    graph.workers = workers

    logger.info("Agent Graph 构建完成 (MAS-plan Command/Send 方案)")
    return graph


async def plan_and_build_initial_state(
    user_input: str,
    intent_detector,
    workers: dict,
    trace_id: str = None,
    trace_callback=None,
) -> tuple[OverallState, List[dict]]:
    """
    首次规划：分析用户意图，生成 planned_tasks

    返回:
    - initial_state: 包含规划好的任务
    - planned_tasks: 任务列表
    """
    from langchain_core.messages import HumanMessage

    # 检测多意图
    intents = await intent_detector.detect_multi_intent(user_input)

    # 映射到 Agent 类型
    agent_map = {
        "search": "search",
        "jira": "jira",
        "log": "log",
        "translate": "translate",
        "summarize": "summarize",
    }

    # 拆分用户输入，获取每个 agent 对应的查询
    split_queries = intent_detector._split_queries(user_input)

    # 构建任务列表和依赖关系
    tasks = []
    seen = set()

    for i, intent in enumerate(intents):
        agent = agent_map.get(intent)
        if not agent or agent in seen:
            continue

        query = split_queries[i] if i < len(split_queries) else user_input

        # 判断依赖：translate/summarize 依赖前一个任务
        depends_on = []
        if agent in ["translate", "summarize"] and tasks:
            prev_task = tasks[-1]
            depends_on = [prev_task["type"]]

        task = {
            "type": agent,
            "depends_on": depends_on,
            "query": query,
        }
        tasks.append(task)
        seen.add(agent)

    logger.info(f"plan_and_build_initial_state: 规划任务 {tasks}")

    state: OverallState = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "planned_tasks": tasks,
        "results": [],
        "streaming_output": None,
        "next_action": "supervisor",
        "trace_id": trace_id,
        "error": None,
        "final_output": None,
        "intent_detector": intent_detector,
        "trace_callback": trace_callback,
        "workers": workers,
    }

    return state, tasks


def create_initial_state(
    user_input: str,
    intent_detector,
    workers: dict,
    trace_id: str = None,
    trace_callback=None,
) -> OverallState:
    """创建初始状态（同步版本，需要先调用 plan_and_build_initial_state）"""
    from langchain_core.messages import HumanMessage

    state: OverallState = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "planned_tasks": [],
        "results": [],
        "streaming_output": None,
        "next_action": "supervisor",
        "trace_id": trace_id,
        "error": None,
        "final_output": None,
        "intent_detector": intent_detector,
        "trace_callback": trace_callback,
        "workers": workers,
    }

    return state
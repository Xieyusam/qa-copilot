"""Join 节点 - 并行执行后汇聚结果"""
from typing import Dict

from app.services.agents.stategraph.state import AgentState
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def join_node(state: AgentState) -> Dict:
    """
    Join 节点 - 等待所有并行 Agent 执行完成，汇聚结果

    在 LangGraph 的 fan-out/fan-in 模式中，join 节点负责：
    1. 等待所有并行的 worker 节点完成
    2. 汇聚它们的结果到 state.results
    3. 将控制权交回 supervisor
    """
    results = state.get("results", {})
    pending_agents = state.get("pending_agents") or []

    logger.info(f"join_node: 汇聚 {len(results)} 个结果, pending={pending_agents}")

    # 这里 results 已经在 worker 节点中被更新了
    # 我们只需要记录汇聚完成

    return {
        # 不需要返回额外的数据，只需要让流程继续到 supervisor
    }

"""Aggregate 节点 - 汇总所有 Agent 结果"""
from typing import Dict

from langchain_core.messages import AIMessage

from app.services.agents.stategraph.state import AgentState
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


async def aggregate_node(state: AgentState) -> Dict:
    """汇总所有 Agent 结果，生成最终回答"""
    results = state.get("results", {})
    context = state.get("context", {})
    intent_chain = context.get("intent_chain", [])
    can_parallel = context.get("can_parallel", [])

    # 判断是串行还是并行：如果 can_parallel 有多个元素且都在 results 中，则是并行
    is_parallel = len(can_parallel) > 1 and all(a in results for a in can_parallel)

    logger.info(f"aggregate_node: results={list(results.keys())}, intent_chain={intent_chain}, can_parallel={can_parallel}, is_parallel={is_parallel}")

    # 串行复合意图（is_parallel=False 且 intent_chain > 1）：返回最后一个 Agent 的结果
    # 并行复合意图（is_parallel=True 且 intent_chain > 1）：拼接所有结果
    if len(intent_chain) > 1 and not is_parallel:
        last_agent = intent_chain[-1]
        if results.get(last_agent):
            final_answer = results[last_agent].answer
            logger.info(f"aggregate_node: 串行链返回最后一个结果 from {last_agent}")
            messages = list(state.get("messages", []))
            messages.append(AIMessage(content=final_answer))
            return {
                "messages": messages,
                "final_answer": final_answer,
            }

    # 并行多意图或单意图：拼接所有结果
    answers = []
    for agent_name, result in results.items():
        if hasattr(result, "answer") and result.answer:
            answers.append(f"【{agent_name.upper()}】\n{result.answer}")

    if not answers:
        final_answer = "没有找到相关信息"
    elif len(answers) == 1:
        final_answer = answers[0]
    else:
        final_answer = "\n\n---\n\n".join(answers)

    logger.info(f"aggregate_node: 汇总结果长度={len(final_answer)}")
    messages = list(state.get("messages", []))
    messages.append(AIMessage(content=final_answer))

    return {
        "messages": messages,
        "final_answer": final_answer,
    }

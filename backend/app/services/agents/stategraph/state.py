"""Agent 状态定义 - LangGraph StateGraph 共享状态 (MAS-plan 方案)

核心改进：
1. results 使用 Annotated[list, operator.add] 自动合并并行结果
2. planned_tasks 声明式依赖替代硬编码的 pending_agents + can_parallel
3. 使用 add_messages 保留对话历史，而非继承 MessagesState
4. streaming_output 用于流式输出当前节点的输出
"""
from typing import TypedDict, Optional, Any, List, Literal, Union
from typing_extensions import Annotated
from langgraph.graph.message import add_messages
from operator import add
from langgraph.types import Command, Send

from app.services.agents.types import Intent, AgentResult


class TaskResult:
    """任务结果封装 - 用于 Annotated list 合并"""
    def __init__(self, agent_type: str, answer: str, sources: list = None):
        self.agent_type = agent_type
        self.answer = answer
        self.sources = sources or []

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "answer": self.answer,
            "sources": self.sources,
        }

    def __repr__(self):
        return f"TaskResult({self.agent_type}, {self.answer[:50]}...)"


class OverallState(TypedDict):
    """
    所有 Agent 节点共享的状态 (MAS-plan 方案)

    核心字段：
    - messages: Annotated[list, add_messages] - 对话历史，自动合并
    - planned_tasks: List[dict] - 声明式任务规划
    - results: Annotated[list, add] - 并行结果自动合并累加
    - streaming_output: str - 当前节点的流式输出
    - final_output: str - 最终回答
    """

    # ==================== 消息历史 ====================
    messages: Annotated[list, add_messages]

    # ==================== 任务规划 ====================
    planned_tasks: List[dict]

    # ==================== 执行结果 ====================
    results: Annotated[List[TaskResult], add]

    # ==================== 流式输出 ====================
    # 当前节点正在输出的内容（用于实时流式传输给前端）
    streaming_output: Optional[str]

    # ==================== 用户输入 ====================
    user_input: str

    # ==================== 元信息 ====================
    trace_id: Optional[str]
    error: Optional[str]

    # 最终回答（用于流式输出）
    final_output: Optional[str]

    # 下一步行动（supervisor 设置，条件边读取）
    next_action: str

    # ==================== Agent 实例引用 ====================
    intent_detector: Any
    trace_callback: Any
    workers: Any


# 兼容性别名
AgentState = OverallState


# Supervisor 返回类型：Command 用于跳转，Send 用于并行
SupervisorReturn = Union[
    Command[Literal["aggregate", "supervisor"]],
    List[Send],
]


def create_initial_state(
    user_input: str,
    intent_detector,
    workers: dict,
    trace_id: str = None,
    trace_callback=None,
) -> OverallState:
    """创建初始状态"""
    from langchain_core.messages import HumanMessage

    state: OverallState = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "planned_tasks": [],
        "results": [],
        "next_action": "supervisor",
        "trace_id": trace_id,
        "error": None,
        "final_output": None,
        "intent_detector": intent_detector,
        "trace_callback": trace_callback,
        "workers": workers,
    }

    return state
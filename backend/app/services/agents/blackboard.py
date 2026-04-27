"""共享黑板 - 多 Agent 通信机制"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class BlackboardMessage:
    """黑板消息记录"""
    type: str  # write, read, clear
    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    agent: str = ""  # 触发该操作的 agent


class Blackboard:
    """
    共享黑板 - 所有 Agent 通过黑板进行通信

    设计原则：
    1. 每个 Agent 只关心自己相关的 key（如 search:query, search:result）
    2. 不需要知道其他 Agent 的存在
    3. 支持并行和串行意图
    4. 所有数据都是 primitive 类型，可以序列化
    """

    def __init__(self, trace_id: str = ""):
        self._data: dict[str, Any] = {}
        self._messages: list[BlackboardMessage] = []
        self._trace_id = trace_id or str(uuid.uuid4())
        self._lock = False  # 防止并发写入

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def write(self, key: str, value: Any, agent: str = "") -> None:
        """
        写入数据到黑板

        Args:
            key: 键名，格式 "agent:field"，如 "search:result"
            value: 值（应该是可序列化的类型）
            agent: 写入的 agent 名称
        """
        if self._lock:
            raise RuntimeError("Blackboard is locked for reading")

        self._data[key] = value
        self._messages.append(BlackboardMessage(
            type="write",
            key=key,
            value=value,
            agent=agent
        ))

    def read(self, key: str) -> Any:
        """
        从黑板读取数据

        Args:
            key: 键名

        Returns:
            值，如果不存在返回 None
        """
        self._messages.append(BlackboardMessage(
            type="read",
            key=key,
            value=None
        ))
        return self._data.get(key)

    def read_by_pattern(self, pattern: str) -> dict[str, Any]:
        """
        按模式读取数据

        Args:
            pattern: glob 模式，如 "search:*" 或 "*:result"

        Returns:
            匹配的 key-value 字典
        """
        import fnmatch
        result = {}
        for key, value in self._data.items():
            if fnmatch.fnmatch(key, pattern):
                result[key] = value
        return result

    def get_messages(self) -> list[BlackboardMessage]:
        """获取所有消息记录"""
        return self._messages.copy()

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            "trace_id": self._trace_id,
            "data": self._data,
            "messages_count": len(self._messages)
        }

    def lock(self) -> None:
        """锁定黑板，防止写入"""
        self._lock = True

    def unlock(self) -> None:
        """解锁黑板"""
        self._lock = False

    def clear(self) -> None:
        """清空黑板"""
        self._data.clear()
        self._messages.clear()


def create_blackboard(state: dict) -> Blackboard:
    """从 state 获取或创建 Blackboard"""
    if "blackboard" not in state:
        state["blackboard"] = Blackboard()
    return state["blackboard"]


def get_agent_result_key(agent_name: str) -> str:
    """获取 Agent 结果的 key"""
    return f"{agent_name}:result"


def get_agent_query_key(agent_name: str) -> str:
    """获取 Agent 查询的 key"""
    return f"{agent_name}:query"


def get_agent_task_key(agent_name: str) -> str:
    """获取 Agent 任务的 key"""
    return f"{agent_name}:task"

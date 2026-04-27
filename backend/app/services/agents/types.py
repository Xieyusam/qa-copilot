"""Agent 相关的数据类型定义"""
from dataclasses import dataclass, field
from typing import Optional

from app.core.schemas import SourceRef


@dataclass
class AgentResult:
    """Agent 执行结果"""
    type: str  # "search", "jira", "log", "translate", "summarize"
    answer: str  # Agent 返回的答案
    sources: list[SourceRef] = field(default_factory=list)  # 来源信息


@dataclass
class Intent:
    """用户意图"""
    type: str  # "search", "jira", "log", "translate", "summarize"
    query: str  # 具体的查询
    depends_on: Optional[str] = None  # 依赖的 intent type，如 "search"

    def __hash__(self):
        return hash((self.type, self.query))

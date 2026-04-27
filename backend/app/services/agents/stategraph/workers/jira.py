"""Jira Worker - JIRA 查询 Worker"""
from typing import Optional

from app.services.agents.types import AgentResult
from app.services.agents.stategraph.workers.base import WorkerAgent
from app.services.integrations.jira_client import JiraClient
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class JiraWorker(WorkerAgent):
    """Jira Worker - JIRA 查询专家"""

    def __init__(self, llm, jira_client: JiraClient, trace_callback=None):
        super().__init__(name="jira", llm=llm, trace_callback=trace_callback)
        self.jira_client = jira_client

    @property
    def system_prompt(self) -> str:
        return """你是一个 JIRA 项目管理专家。

你的职责：
1. 回答关于 JIRA 项目、Issue、Bug 等相关问题
2. 提供准确的 JIRA 信息

回答规范：
- 简洁明了
- 如涉及项目名称、Issue ID 等，使用加粗或代码格式
- 如果查询失败，说明错误原因"""

    async def _execute_impl(
        self,
        query: str,
        context: Optional[dict] = None,
        **kwargs
    ) -> AgentResult:
        """执行 JIRA 查询"""
        try:
            # 根据 query 内容决定调用哪个 JIRA 方法
            query_lower = query.lower()

            if "项目" in query or "project" in query_lower:
                result = await self.jira_client.get_projects()
            elif "issue" in query_lower or "bug" in query_lower or "PROJ-" in query:
                # 提取 issue key
                import re
                match = re.search(r'[A-Z]+-\d+', query)
                if match:
                    result = await self.jira_client.get_issue(match.group())
                else:
                    result = await self.jira_client.search_issues(query)
            else:
                result = await self.jira_client.get_projects()

            return AgentResult(
                type="jira",
                answer=result,
                sources=[],
            )

        except Exception as e:
            logger.error(f"JiraWorker 执行失败: {e}")
            raise

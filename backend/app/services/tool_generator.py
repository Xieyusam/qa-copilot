"""
动态工具生成器：根据数据库分类动态生成知识库检索工具。
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool, tool
from pydantic import BaseModel, Field

from app.db.session import SessionLocal
from app.models.kb_category import KbCategory
from app.services.hybrid_retriever import HybridRetriever
from app.services.jira_client import JiraClient


class QueryInput(BaseModel):
    """检索工具输入参数。"""
    query: str = Field(description="检索查询文本")


class ToolGenerator:
    """根据数据库分类动态生成检索工具。"""

    def __init__(self, retriever: HybridRetriever):
        self._retriever = retriever

    def build_retrieve_tools(self, db) -> list:
        """生成所有知识库检索工具。"""
        categories = db.query(KbCategory).all()
        tools = []

        for cat in categories:
            tool = self._create_tool_for_category(cat)
            tools.append(tool)

        return tools

    def _create_tool_for_category(self, category: KbCategory) -> StructuredTool:
        """为单个分类创建检索工具。"""
        # 生成工具名称（如 retrieve_qa_docs_kb）
        safe_name = category.name.lower().replace("-", "_").replace(" ", "_")
        tool_name = f"retrieve_{safe_name}_kb"

        # 构建工具描述
        description = self._build_tool_description(category)

        # 使用闭包捕获 category
        async def retrieve_func(query: str) -> tuple[str, list[dict]]:
            chunks = await self._retriever.retrieve(
                query,
                top_k=5,
                filter={"kb_category_id": category.id}
            )
            if not chunks:
                return f"未找到相关文档（分类：{category.name}）", []

            text = "\n\n".join(
                f"[来源: {c.filename}, 位置: {c.position}]\n{c.content}"
                for c in chunks
            )
            artifact = [
                {
                    "doc_id": c.doc_id,
                    "filename": c.filename,
                    "position": c.position,
                    "score": c.score,
                    "content": c.content,
                }
                for c in chunks
            ]
            return text, artifact

        # 使用 StructuredTool.from_function 创建工具
        return StructuredTool.from_function(
            coroutine=retrieve_func,
            name=tool_name,
            description=description,
            args_schema=QueryInput,
            response_format="content_and_artifact",
        )

    def _build_tool_description(self, category: KbCategory) -> str:
        """构建工具描述。"""
        desc_parts = [f"从【{category.name}】知识库中检索相关文档片段。"]

        if category.description:
            desc_parts.append(f"该知识库存放：{category.description}")

        # 添加使用场景说明
        desc_parts.append("""
适用场景：
- 查询项目资料、团队信息、参与人员
- 查询技术文档、操作指南、使用手册
- 查询平台功能说明、配置文档
- 查询已存储的任何文档内容

注意：此工具用于检索知识库中的文档，不查询 Jira 系统。""")

        return " ".join(desc_parts)


def build_jira_tools(jira_client: JiraClient) -> list:
    """构建 Jira 相关工具。"""
    tools = []

    @tool(response_format="content_and_artifact")
    async def query_jira(jql: str, max_results: int = 10) -> tuple[str, list[dict]]:
        """执行 JQL 查询并返回 Jira 问题列表。

        仅用于查询 Jira 系统中的任务/问题/Bug。
        不适用于查询项目资料、团队信息（请使用知识库检索工具）。

        参数:
            jql: JQL 查询语句（如 "project = PROJ AND status = Open"）
            max_results: 返回结果的最大数量（默认 10，最大 50）
        """
        max_results = min(max_results, 50)
        result = await jira_client.search_issues(jql, max_results=max_results)
        return result, []

    @tool(response_format="content_and_artifact")
    async def get_jira_issue(issue_key: str) -> tuple[str, list[dict]]:
        """获取指定 Jira 问题的详情（如 'PROJ-123'）。

        仅用于查询 Jira 系统中的特定问题。
        """
        result = await jira_client.get_issue(issue_key)
        return result, []

    @tool(response_format="content_and_artifact")
    async def list_jira_projects() -> tuple[str, list[dict]]:
        """获取 Jira 系统中所有可访问的项目（项目 Key 和名称）。

        仅用于查看 Jira 系统的项目列表。
        如需查询项目资料、团队信息，请使用知识库检索工具。
        """
        result = await jira_client.get_projects()
        return result, []

    @tool(response_format="content_and_artifact")
    async def count_jira_issues(jql: str) -> tuple[str, list[dict]]:
        """统计匹配 JQL 条件的 Jira 问题数量（仅返回数量，不返回问题详情）。

        仅用于统计 Jira 系统中的任务/问题数量。
        不适用于查询项目资料（请使用知识库检索工具）。

        参数:
            jql: JQL 查询语句（如 "project = PROJ AND resolution = Unresolved"）
        """
        result = await jira_client.count_issues(jql)
        if isinstance(result, dict):
            return f"数量: {result['count']} (JQL: {result['jql']})", [result]
        return result, []

    tools.extend([query_jira, get_jira_issue, list_jira_projects, count_jira_issues])
    return tools
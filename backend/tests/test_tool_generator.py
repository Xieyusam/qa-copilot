"""
动态工具生成器测试。
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.tool_generator import ToolGenerator, build_jira_tools
from app.services.hybrid_retriever import HybridRetriever
from app.services.jira_client import JiraClient
from app.models.kb_category import KbCategory


class TestToolGenerator:
    """ToolGenerator 测试类。"""

    def test_build_retrieve_tools_returns_list(self, db_session):
        """build_retrieve_tools 应返回工具列表。"""
        mock_retriever = MagicMock(spec=HybridRetriever)

        generator = ToolGenerator(mock_retriever)
        tools = generator.build_retrieve_tools(db_session)

        assert isinstance(tools, list)
        # 应该有 3 个默认分类
        assert len(tools) >= 3

    def test_tool_names_follow_pattern(self, db_session):
        """工具名称应遵循 retrieve_{category}_kb 模式。"""
        mock_retriever = MagicMock(spec=HybridRetriever)

        generator = ToolGenerator(mock_retriever)
        tools = generator.build_retrieve_tools(db_session)

        tool_names = [t.name for t in tools]
        assert "retrieve_default_kb" in tool_names
        assert "retrieve_translation_kb" in tool_names
        assert "retrieve_log_kb" in tool_names

    def test_tool_has_description(self, db_session):
        """工具应有描述。"""
        mock_retriever = MagicMock(spec=HybridRetriever)

        generator = ToolGenerator(mock_retriever)
        tools = generator.build_retrieve_tools(db_session)

        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 0
            assert "知识库" in tool.description

    def test_build_tools_with_custom_category(self, db_session):
        """自定义分类应生成对应工具。"""
        # 创建自定义分类（使用唯一名称）
        import uuid
        unique_name = f"custom-test-{uuid.uuid4().hex[:8]}"
        custom_cat = KbCategory(
            id=unique_name,
            name=unique_name,
            description="自定义测试分类",
        )
        db_session.add(custom_cat)
        db_session.commit()

        mock_retriever = MagicMock(spec=HybridRetriever)

        generator = ToolGenerator(mock_retriever)
        tools = generator.build_retrieve_tools(db_session)

        tool_names = [t.name for t in tools]
        expected_name = f"retrieve_{unique_name.replace('-', '_')}_kb"
        assert expected_name in tool_names

    @pytest.mark.asyncio
    async def test_tool_calls_retriever(self, db_session):
        """工具应调用 retriever.retrieve 方法。"""
        mock_retriever = MagicMock(spec=HybridRetriever)
        mock_retriever.retrieve = AsyncMock(return_value=[])

        generator = ToolGenerator(mock_retriever)
        tools = generator.build_retrieve_tools(db_session)

        # 找到 default 工具并调用
        default_tool = next(t for t in tools if t.name == "retrieve_default_kb")
        result = await default_tool.coroutine("test query")

        mock_retriever.retrieve.assert_called_once()
        call_args = mock_retriever.retrieve.call_args
        assert call_args.args[0] == "test query"
        assert call_args.kwargs["filter"]["kb_category_id"] == "default"


class TestJiraTools:
    """Jira 工具测试类。"""

    def test_build_jira_tools_returns_list(self):
        """build_jira_tools 应返回工具列表。"""
        mock_jira = MagicMock(spec=JiraClient)

        tools = build_jira_tools(mock_jira)

        assert isinstance(tools, list)
        assert len(tools) == 4

    def test_jira_tool_names(self):
        """Jira 工具应有正确的名称。"""
        mock_jira = MagicMock(spec=JiraClient)

        tools = build_jira_tools(mock_jira)
        tool_names = [t.name for t in tools]

        assert "query_jira" in tool_names
        assert "get_jira_issue" in tool_names
        assert "list_jira_projects" in tool_names
        assert "count_jira_issues" in tool_names
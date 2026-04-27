"""Worker Agents 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.stategraph.workers.search import SearchWorker
from app.services.agents.stategraph.workers.jira import JiraWorker
from app.services.agents.stategraph.workers.log import LogWorker
from app.services.agents.types import AgentResult


class TestSearchWorker:
    """SearchWorker 测试"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="云测平台是一个...")
        llm.bind_tools = MagicMock(return_value=MagicMock(ainvoke=AsyncMock(
            return_value=MagicMock(
                content="",
                tool_calls=[]
            )
        )))
        return llm

    @pytest.fixture
    def mock_kb_tool_registry(self):
        """Mock KB Tool Registry"""
        registry = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "kb_test"
        mock_tool.description = "测试知识库"
        mock_tool.arun = AsyncMock(return_value="【测试文件】云测平台简介内容")
        registry.get_search_tools = MagicMock(return_value=[mock_tool])
        return registry

    @pytest.fixture
    def worker(self, mock_llm, mock_kb_tool_registry):
        return SearchWorker(llm=mock_llm, kb_tool_registry=mock_kb_tool_registry)

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, worker):
        """测试执行返回结果"""
        result = await worker.execute(query="云测平台是什么")

        assert isinstance(result, AgentResult)
        assert result.type == "search"
        assert result.answer == "云测平台是一个..."

    @pytest.mark.asyncio
    async def test_execute_no_tools(self):
        """测试无可用工具"""
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=MagicMock(ainvoke=AsyncMock(
            return_value=MagicMock(content="", tool_calls=[])
        )))
        registry = MagicMock()
        registry.get_search_tools = MagicMock(return_value=[])

        worker = SearchWorker(llm=mock_llm, kb_tool_registry=registry)
        result = await worker.execute(query="云测平台是什么")

        assert result.type == "search"
        assert "没有可用的知识库" in result.answer

    @pytest.mark.asyncio
    async def test_trace_callback(self, worker):
        """测试 trace 回调"""
        trace_callback = MagicMock()
        worker.trace_callback = trace_callback

        await worker.execute(query="测试")

        trace_callback.assert_called()
        call_kwargs = trace_callback.call_args[1]
        assert call_kwargs["tool_name"] == "search"


class TestJiraWorker:
    """JiraWorker 测试"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="JIRA 查询结果...")
        return llm

    @pytest.fixture
    def mock_jira_client(self):
        """Mock JIRA Client"""
        client = MagicMock()
        client.get_projects = AsyncMock(return_value="共 23 个项目")
        client.get_issue = AsyncMock(return_value="PROJ-123: Test issue\nStatus: Open")
        client.search_issues = AsyncMock(return_value="找到 10 个 issues")
        return client

    @pytest.fixture
    def worker(self, mock_llm, mock_jira_client):
        return JiraWorker(llm=mock_llm, jira_client=mock_jira_client)

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, worker):
        """测试执行返回结果 - 匹配项目查询"""
        result = await worker.execute(query="jira有哪些项目")

        assert isinstance(result, AgentResult)
        assert result.type == "jira"
        assert result.answer == "共 23 个项目"

    @pytest.mark.asyncio
    async def test_execute_error(self, worker, mock_jira_client):
        """测试执行错误"""
        mock_jira_client.get_projects = AsyncMock(side_effect=Exception("JIRA 连接失败"))

        result = await worker.execute(query="jira有哪些项目")

        assert result.type == "jira"
        assert "失败" in result.answer


class TestLogWorker:
    """LogWorker 测试"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="分析结果：发现 3 个错误...")
        return llm

    @pytest.fixture
    def worker(self, mock_llm):
        return LogWorker(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, worker):
        """测试执行返回结果"""
        result = await worker.execute(query="分析最近的日志")

        assert isinstance(result, AgentResult)
        assert result.type == "log"
        assert "分析结果" in result.answer

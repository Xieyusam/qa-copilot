"""Supervisor Agent 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.stategraph.supervisor.agent import SupervisorAgent
from app.services.agents.intent_detector import IntentDetector
from app.services.agents.types import AgentResult


class TestSupervisorAgent:
    """SupervisorAgent 测试"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="search")
        return llm

    @pytest.fixture
    def mock_intent_detector(self):
        """Mock IntentDetector"""
        detector = MagicMock(spec=IntentDetector)
        detector.detect_multi_intent = MagicMock(return_value=["search", "jira"])
        return detector

    @pytest.fixture
    def supervisor(self, mock_llm, mock_intent_detector):
        return SupervisorAgent(
            llm=mock_llm,
            intent_detector=mock_intent_detector,
        )

    @pytest.mark.asyncio
    async def test_decide_with_pending_agents(self, supervisor):
        """测试有待执行列表时直接返回"""
        result = await supervisor.decide(
            user_input="查一下",
            existing_results={},
            pending_agents=["search", "jira"],
        )

        assert result == "search"

    @pytest.mark.asyncio
    async def test_decide_with_intent_detection(self, supervisor, mock_intent_detector):
        """测试意图检测"""
        mock_intent_detector.detect_multi_intent = AsyncMock(return_value=["jira"])

        result = await supervisor.decide(
            user_input="查 jira 项目",
            existing_results={},
            pending_agents=[],
        )

        assert result == "jira"

    @pytest.mark.asyncio
    async def test_decide_no_intents_aggregates(self, supervisor, mock_intent_detector):
        """测试无意图时返回 aggregate"""
        mock_intent_detector.detect_multi_intent = AsyncMock(return_value=[])

        result = await supervisor.decide(
            user_input="你好",
            existing_results={},
            pending_agents=[],
        )

        assert result == "aggregate"

    @pytest.mark.asyncio
    async def test_aggregate(self, supervisor):
        """测试汇总功能"""
        mock_llm = supervisor.llm
        mock_llm.chat = AsyncMock(return_value="这是汇总后的结果")

        results = {
            "search": AgentResult(type="search", answer="搜索结果", sources=[]),
            "jira": AgentResult(type="jira", answer="JIRA 结果", sources=[]),
        }

        answer = await supervisor.aggregate(
            user_input="查一下项目",
            results=results,
        )

        assert answer == "这是汇总后的结果"
        mock_llm.chat.assert_called_once()

    def test_format_results(self, supervisor):
        """测试结果格式化"""
        results = {
            "search": AgentResult(type="search", answer="搜索结果", sources=[]),
        }

        formatted = supervisor._format_results(results)

        assert "【search】" in formatted
        assert "搜索结果" in formatted

    def test_format_results_empty(self, supervisor):
        """测试空结果格式化"""
        formatted = supervisor._format_results({})
        assert "暂无执行结果" in formatted

    @pytest.mark.asyncio
    async def test_decide_trace_callback(self, supervisor):
        """测试 trace 回调"""
        trace_callback = MagicMock()
        supervisor.trace_callback = trace_callback

        await supervisor.decide(
            user_input="测试",
            existing_results={},
            pending_agents=["search"],
        )

        trace_callback.assert_called()
        call_kwargs = trace_callback.call_args[1]
        assert call_kwargs["tool_name"] == "supervisor"

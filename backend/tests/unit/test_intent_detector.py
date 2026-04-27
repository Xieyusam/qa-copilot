"""IntentDetector 单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.intent_detector import IntentDetector, detect_intent_by_rules


class TestDetectIntentByRules:
    """规则检测测试"""

    def test_detect_jira_keywords(self):
        """测试 JIRA 关键词检测"""
        test_cases = [
            ("查jira有哪些项目", "jira"),
            ("jira有哪些项目", "jira"),
            ("查一下 PROJ-123 的 bug", "jira"),
            ("查询 issue", "jira"),
            ("查看 epic", "jira"),
            ("sprint 列表", "jira"),
        ]

        for query, expected in test_cases:
            result = detect_intent_by_rules(query)
            assert result == expected, f"Expected {expected} for '{query}', got {result}"

    def test_detect_log_keywords(self):
        """测试日志关键词检测"""
        test_cases = [
            ("分析最近的错误日志", "log"),
            ("查看 exception", "log"),
            ("logs 文件分析", "log"),
            ("error 日志", "log"),
        ]

        for query, expected in test_cases:
            result = detect_intent_by_rules(query)
            assert result == expected, f"Expected {expected} for '{query}', got {result}"

    def test_detect_translate_keywords(self):
        """测试翻译关键词检测"""
        test_cases = [
            ("翻译成英文", "translate"),
            ("把这段话翻译一下", "translate"),
            ("translate to Chinese", "translate"),
            ("翻译成中文", "translate"),
        ]

        for query, expected in test_cases:
            result = detect_intent_by_rules(query)
            assert result == expected, f"Expected {expected} for '{query}', got {result}"

    def test_detect_summarize_keywords(self):
        """测试摘要关键词检测"""
        test_cases = [
            ("总结一下", "summarize"),
            ("生成摘要", "summarize"),
            ("概括主要内容", "summarize"),
            ("提炼要点", "summarize"),
        ]

        for query, expected in test_cases:
            result = detect_intent_by_rules(query)
            assert result == expected, f"Expected {expected} for '{query}', got {result}"

    def test_detect_no_match_returns_none(self):
        """测试无匹配时返回 None"""
        result = detect_intent_by_rules("云测平台有哪些功能")
        assert result is None


class TestIntentDetector:
    """IntentDetector 完整功能测试"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        client = MagicMock()
        client.chat = AsyncMock(return_value="search")
        return client

    @pytest.fixture
    def detector(self, mock_llm_client):
        return IntentDetector(mock_llm_client)

    @pytest.mark.asyncio
    async def test_detect_single_intent_jira(self, detector):
        """测试单意图检测 - jira"""
        result = await detector.detect("jira有哪些项目")
        assert result == "jira"

    @pytest.mark.asyncio
    async def test_detect_single_intent_search(self, detector):
        """测试单意图检测 - search（默认）"""
        result = await detector.detect("云测平台有哪些功能")
        assert result == "search"

    def test_split_queries_by_comma(self, detector):
        """测试逗号分隔"""
        queries = detector._split_queries("查jira项目，同时查云测平台")
        assert len(queries) == 2

    def test_split_queries_by_and(self, detector):
        """测试 '和' 分隔"""
        queries = detector._split_queries("查jira项目、和云测平台")
        assert len(queries) == 2

    @pytest.mark.asyncio
    async def test_detect_multi_intent_parallel(self, detector):
        """测试多意图并行检测"""
        intents = await detector.detect_multi_intent("查jira有哪些项目，同时查云测平台")
        assert len(intents) == 2
        assert "jira" in intents
        assert "search" in intents

    @pytest.mark.asyncio
    async def test_llm_fallback(self, mock_llm_client):
        """测试 LLM 兜底"""
        # 设置 LLM 返回 jira
        mock_llm_client.chat = AsyncMock(return_value="jira")

        detector = IntentDetector(mock_llm_client)
        result = await detector._llm_detect("PROJ-123 相关的问题")

        assert result == "jira"
        mock_llm_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_fallback_invalid_response(self, mock_llm_client):
        """测试 LLM 返回无效值时的兜底"""
        mock_llm_client.chat = AsyncMock(return_value="invalid_type")

        detector = IntentDetector(mock_llm_client)
        result = await detector._llm_detect("一些问题")

        # 应该返回默认的 search
        assert result == "search"

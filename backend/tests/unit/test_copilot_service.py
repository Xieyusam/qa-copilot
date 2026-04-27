import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.core.copilot_service import CopilotService
from app.services.agents.types import Intent, AgentResult
from app.core.schemas import SourceRef


@pytest.mark.asyncio
async def test_copilot_instantiation():
    """测试 CopilotService 实例化"""
    retriever = MagicMock()
    conv = MagicMock()
    llm = MagicMock()
    jira = MagicMock()
    service = CopilotService(retriever, conv, llm, jira)
    assert service is not None
    # 检查 StateGraph 相关组件已初始化
    assert service._graph is not None
    # V2: 使用 intent_detector 而非 supervisor
    assert service._intent_detector is not None
    assert service._search_worker is not None
    assert service._jira_worker is not None
    assert service._log_worker is not None


@pytest.mark.asyncio
async def test_copilot_has_stategraph():
    """测试 CopilotService 包含 StateGraph"""
    service = CopilotService()
    # 检查有 graph 实例
    assert hasattr(service, "_graph")
    # graph 应该可以被调用
    assert callable(service._graph.invoke)


@pytest.mark.asyncio
async def test_copilot_workers_initialized():
    """测试 Worker Agents 已正确初始化"""
    service = CopilotService()

    # 检查 workers
    assert service._search_worker is not None
    assert service._jira_worker is not None
    assert service._log_worker is not None

    # V2: 使用 intent_detector 而非 supervisor agent
    assert service._intent_detector is not None


@pytest.mark.asyncio
async def test_agent_result_dataclass():
    """测试 AgentResult 数据类"""
    result = AgentResult(
        type="search",
        answer="测试答案",
        sources=[],
    )
    assert result.type == "search"
    assert result.answer == "测试答案"
    assert result.sources == []


@pytest.mark.asyncio
async def test_intent_dataclass():
    """测试 Intent 数据类"""
    intent = Intent(
        type="search",
        query="测试查询",
        depends_on=None,
    )
    assert intent.type == "search"
    assert intent.query == "测试查询"
    assert intent.depends_on is None


@pytest.mark.asyncio
async def test_search_worker_execute():
    """测试 SearchWorker 执行"""
    from app.services.agents.stategraph.workers.search import SearchWorker
    from app.services.agents.kb_tool_registry import KbToolRegistry

    llm = MagicMock()
    llm.chat = AsyncMock(return_value="云测平台是一个测试平台")
    llm.bind_tools = MagicMock(return_value=MagicMock(ainvoke=AsyncMock(
        return_value=MagicMock(content="", tool_calls=[])
    )))

    # Mock KB Tool Registry
    kb_registry = MagicMock()
    mock_tool = MagicMock()
    mock_tool.name = "kb_test"
    mock_tool.description = "测试知识库"
    mock_tool.arun = AsyncMock(return_value="【测试文件】云测平台内容")
    kb_registry.get_search_tools = MagicMock(return_value=[mock_tool])

    worker = SearchWorker(llm=llm, kb_tool_registry=kb_registry)
    result = await worker.execute("云测平台简介")

    assert result.type == "search"
    assert result.answer == "云测平台是一个测试平台"


@pytest.mark.asyncio
async def test_intent_detector_rule_match():
    """测试 IntentDetector 规则匹配"""
    from app.services.agents.intent_detector import detect_intent_by_rules

    # JIRA 关键词
    assert detect_intent_by_rules("查 jira 有哪些项目") == "jira"
    assert detect_intent_by_rules("PROJ-123 bug") == "jira"

    # LOG 关键词
    assert detect_intent_by_rules("分析错误日志") == "log"

    # TRANSLATE 关键词
    assert detect_intent_by_rules("翻译成英文") == "translate"

    # SUMMARIZE 关键词
    assert detect_intent_by_rules("总结一下") == "summarize"


@pytest.mark.asyncio
async def test_copilot_intent_detector_integration():
    """测试 CopilotService 中的 IntentDetector"""
    service = CopilotService()

    # 测试检测
    result = await service._intent_detector.detect("查 jira 项目")
    assert result == "jira"

    # 测试多意图检测
    results = await service._intent_detector.detect_multi_intent("查 jira 项目，同时查云测平台")
    assert "jira" in results
    assert "search" in results

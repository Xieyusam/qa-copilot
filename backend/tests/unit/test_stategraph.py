"""StateGraph 单元测试 - MAS-plan 方案"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.agents.stategraph.graph import (
    build_agent_graph,
    create_initial_state,
)
from app.services.agents.stategraph.state import OverallState, TaskResult


class TestCreateInitialState:
    """create_initial_state 测试"""

    def test_create_initial_state_basic(self):
        """测试基础状态创建"""
        intent_detector = MagicMock()
        search_worker = MagicMock()
        jira_worker = MagicMock()
        log_worker = MagicMock()

        workers = {
            "search": search_worker,
            "jira": jira_worker,
            "log": log_worker,
        }

        state = create_initial_state(
            user_input="测试问题",
            intent_detector=intent_detector,
            workers=workers,
            trace_id="trace-123",
        )

        assert state["user_input"] == "测试问题"
        assert state["intent_detector"] == intent_detector
        assert state["workers"] == workers
        assert state["planned_tasks"] == []
        assert state["results"] == []
        assert state["next_action"] == "supervisor"
        assert state["trace_id"] == "trace-123"

    def test_create_initial_state_with_workers(self):
        """测试带可选 worker 的状态创建"""
        intent_detector = MagicMock()
        search_worker = MagicMock()
        jira_worker = MagicMock()
        log_worker = MagicMock()
        translate_worker = MagicMock()

        workers = {
            "search": search_worker,
            "jira": jira_worker,
            "log": log_worker,
            "translate": translate_worker,
        }

        state = create_initial_state(
            user_input="测试问题",
            intent_detector=intent_detector,
            workers=workers,
        )

        assert state["workers"]["translate"] == translate_worker
        assert state["planned_tasks"] == []


class TestBuildAgentGraph:
    """build_agent_graph 测试"""

    @pytest.fixture
    def mock_agents(self):
        """Mock 所有 agent"""
        intent_detector = MagicMock()
        search_worker = MagicMock()
        jira_worker = MagicMock()
        log_worker = MagicMock()
        return intent_detector, search_worker, jira_worker, log_worker

    def test_build_graph_returns_compiled_graph(self, mock_agents):
        """测试图构建返回编译后的图"""
        intent_detector, search_worker, jira_worker, log_worker = mock_agents

        workers = {
            "search": search_worker,
            "jira": jira_worker,
            "log": log_worker,
        }

        graph = build_agent_graph(
            intent_detector=intent_detector,
            search_worker=search_worker,
            jira_worker=jira_worker,
            log_worker=log_worker,
        )

        # 检查返回的是编译后的图
        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")

    def test_build_graph_with_optional_workers(self, mock_agents):
        """测试带可选 worker 的图构建"""
        intent_detector, search_worker, jira_worker, log_worker = mock_agents
        translate_worker = MagicMock()

        graph = build_agent_graph(
            intent_detector=intent_detector,
            search_worker=search_worker,
            jira_worker=jira_worker,
            log_worker=log_worker,
            translate_worker=translate_worker,
        )

        assert graph is not None


class TestOverallState:
    """OverallState 测试"""

    def test_task_result_creation(self):
        """测试 TaskResult 创建"""
        result = TaskResult(
            agent_type="search",
            answer="测试答案",
            sources=[],
        )
        assert result.agent_type == "search"
        assert result.answer == "测试答案"
        assert result.sources == []

    def test_task_result_with_sources(self):
        """测试带 sources 的 TaskResult"""
        from app.core.schemas import SourceRef
        source = SourceRef(
            doc_id="doc1",
            filename="test.txt",
            chunk_position=1,
            similarity_score=0.9,
            content="测试内容",
        )
        result = TaskResult(
            agent_type="search",
            answer="测试答案",
            sources=[source],
        )
        assert len(result.sources) == 1
        assert result.sources[0].doc_id == "doc1"

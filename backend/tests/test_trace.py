"""
Tests for Trace models and CopilotService trace recording.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.models.trace import AgentTrace, TraceStep
from app.models.feedback import ChatFeedback


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

def test_agent_trace_creation():
    """AgentTrace should be created with correct attributes."""
    trace = AgentTrace(
        id="trace-1",
        session_id="session-1",
        question="What is AI?",
        final_answer="AI stands for Artificial Intelligence.",
        total_time_ms=500.0,
        created_at=datetime.utcnow(),
    )

    assert trace.id == "trace-1"
    assert trace.session_id == "session-1"
    assert trace.question == "What is AI?"
    assert trace.final_answer == "AI stands for Artificial Intelligence."
    assert trace.total_time_ms == 500.0
    assert trace.created_at is not None


def test_agent_trace_default_values():
    """AgentTrace should accept optional final_answer and total_time_ms."""
    trace = AgentTrace(
        id="trace-2",
        session_id="session-2",
        question="Test question",
        created_at=datetime.utcnow(),
    )

    # When instantiated directly, optional fields can be None
    assert trace.question == "Test question"
    assert trace.final_answer is None


def test_trace_step_creation():
    """TraceStep should be created with correct attributes."""
    step = TraceStep(
        id="step-1",
        trace_id="trace-1",
        step_index=0,
        step_type="tool_call",
        tool_name="retrieve_default_kb",
        input_prompt="search query",
        output_result="found documents",
        time_ms=250.0,
    )

    assert step.id == "step-1"
    assert step.trace_id == "trace-1"
    assert step.step_index == 0
    assert step.step_type == "tool_call"
    assert step.tool_name == "retrieve_default_kb"
    assert step.input_prompt == "search query"
    assert step.output_result == "found documents"
    assert step.time_ms == 250.0


def test_trace_step_optional_fields():
    """TraceStep optional fields should be nullable."""
    step = TraceStep(
        id="step-2",
        trace_id="trace-1",
        step_index=1,
        step_type="llm_stream",
        time_ms=100.0,
    )

    assert step.tool_name is None
    assert step.input_prompt is None
    assert step.output_result is None


def test_chat_feedback_creation():
    """ChatFeedback should be created with correct attributes."""
    feedback = ChatFeedback(
        id="fb-1",
        session_id="session-1",
        message_index=2,
        feedback_type="positive",
        user_id="user-1",
        created_at=datetime.utcnow(),
    )

    assert feedback.id == "fb-1"
    assert feedback.session_id == "session-1"
    assert feedback.message_index == 2
    assert feedback.feedback_type == "positive"
    assert feedback.user_id == "user-1"
    assert feedback.created_at is not None


def test_chat_feedback_types():
    """ChatFeedback should accept positive and negative types."""
    positive = ChatFeedback(
        id="fb-pos",
        session_id="s1",
        message_index=0,
        feedback_type="positive",
        user_id="u1",
    )
    negative = ChatFeedback(
        id="fb-neg",
        session_id="s1",
        message_index=1,
        feedback_type="negative",
        user_id="u1",
    )

    assert positive.feedback_type == "positive"
    assert negative.feedback_type == "negative"


# ---------------------------------------------------------------------------
# CopilotService Trace Recording Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_copilot_service_records_trace():
    """CopilotService should record trace during answer generation."""
    from app.services.copilot_service import CopilotService

    # Mock dependencies
    mock_retriever = MagicMock()
    mock_conv = MagicMock()
    mock_conv.get_recent_history.return_value = []

    mock_llm = MagicMock()
    mock_model = MagicMock()

    # Create a mock agent that yields events
    async def mock_astream_events(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=" world")}}
        yield {"event": "on_tool_end", "data": {"output": MagicMock(artifact=[])}, "name": "test_tool"}

    mock_agent = MagicMock()
    mock_agent.astream_events = mock_astream_events
    mock_llm.model = mock_model

    mock_jira = MagicMock()

    # Create service
    service = CopilotService(
        retriever=mock_retriever,
        conversation_manager=mock_conv,
        llm_client=mock_llm,
        jira_client=mock_jira,
    )
    service._agent = mock_agent

    # Mock database
    with patch("app.services.copilot_service.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock trace creation
        mock_trace = MagicMock()
        mock_trace.id = "test-trace-id"
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db.get.return_value = mock_trace

        # Collect results
        results = []
        async for chunk in service.answer("session-1", "Hello?"):
            results.append(chunk)

        # Verify trace was created
        assert mock_db.add.called
        assert mock_db.commit.called


def test_copilot_service_record_step():
    """CopilotService._record_step should save step to database."""
    from app.services.copilot_service import CopilotService

    service = CopilotService()

    with patch("app.services.copilot_service.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        service._record_step(
            trace_id="trace-1",
            step_index=0,
            step_type="tool_call",
            tool_name="retrieve_kb",
            input_prompt="test query",
            time_ms=100.0,
            output_result="found"
        )

        assert mock_db.add.called
        assert mock_db.commit.called


def test_copilot_service_update_trace():
    """CopilotService._update_trace should update final answer and time."""
    from app.services.copilot_service import CopilotService

    service = CopilotService()

    with patch("app.services.copilot_service.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_trace = MagicMock()
        mock_db.get.return_value = mock_trace

        service._update_trace("trace-1", "Final answer", 1500.0)

        assert mock_trace.final_answer == "Final answer"
        assert mock_trace.total_time_ms == 1500.0
        assert mock_db.commit.called


def test_copilot_service_truncate_long_content():
    """CopilotService should truncate long content when recording."""
    from app.services.copilot_service import CopilotService

    service = CopilotService()

    long_input = "x" * 2000
    long_output = "y" * 3000

    with patch("app.services.copilot_service.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        service._record_step(
            trace_id="trace-1",
            step_index=0,
            step_type="tool_call",
            tool_name="test",
            input_prompt=long_input,
            time_ms=100.0,
            output_result=long_output
        )

        # Get the TraceStep that was added
        added_step = mock_db.add.call_args[0][0]
        assert len(added_step.input_prompt) == 1000  # Truncated
        assert len(added_step.output_result) == 2000  # Truncated
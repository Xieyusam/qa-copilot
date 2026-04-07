"""
Tests for Admin API — Observability and Feedback endpoints.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.trace import AgentTrace, TraceStep
from app.models.feedback import ChatFeedback


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def client(override_auth):
    """使用认证 override 的 TestClient。"""
    return TestClient(app)


@pytest.fixture
def sample_trace():
    """Sample AgentTrace for testing."""
    trace = AgentTrace(
        id="trace-1",
        session_id="session-1",
        question="What is RAG?",
        final_answer="RAG stands for Retrieval-Augmented Generation.",
        total_time_ms=1500.0,
        created_at=datetime.utcnow(),
    )
    trace.steps = [
        TraceStep(
            id="step-1",
            trace_id="trace-1",
            step_index=0,
            step_type="llm_start",
            tool_name=None,
            input_prompt="What is RAG?",
            output_result=None,
            time_ms=100.0,
            created_at=datetime.utcnow(),
        ),
        TraceStep(
            id="step-2",
            trace_id="trace-1",
            step_index=1,
            step_type="tool_call",
            tool_name="retrieve_default_kb",
            input_prompt="RAG",
            output_result="Found 3 documents",
            time_ms=800.0,
            created_at=datetime.utcnow(),
        ),
    ]
    return trace


@pytest.fixture
def sample_feedback():
    """Sample ChatFeedback for testing."""
    return ChatFeedback(
        id="feedback-1",
        session_id="session-1",
        message_index=0,
        feedback_type="positive",
        user_id="user-1",
        created_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Traces API Tests
# ---------------------------------------------------------------------------

def test_list_traces_success(client, sample_trace):
    """GET /admin/traces should return list of traces."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock query chain
        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_trace]
        mock_db.query.return_value = mock_query

        resp = client.get("/api/admin/traces")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "trace-1"
    assert data["items"][0]["question"] == "What is RAG?"


def test_list_traces_with_session_filter(client, sample_trace):
    """GET /admin/traces should filter by session_id."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_trace]
        mock_db.query.return_value = mock_query

        resp = client.get("/api/admin/traces?session_id=session-1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_get_trace_detail_success(client, sample_trace):
    """GET /admin/traces/{id} should return trace details with steps."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.get.return_value = sample_trace

        resp = client.get("/api/admin/traces/trace-1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "trace-1"
    assert data["question"] == "What is RAG?"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["step_type"] == "llm_start"
    assert data["steps"][1]["tool_name"] == "retrieve_default_kb"


def test_get_trace_detail_not_found(client):
    """GET /admin/traces/{id} should return 404 if not found."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.get.return_value = None

        resp = client.get("/api/admin/traces/nonexistent")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Trace not found"


def test_export_trace_success(client, sample_trace):
    """GET /admin/traces/{id}/export should return JSON download."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.get.return_value = sample_trace

        resp = client.get("/api/admin/traces/trace-1/export")

    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    data = resp.json()
    assert data["id"] == "trace-1"
    assert "steps" in data


# ---------------------------------------------------------------------------
# Feedbacks API Tests
# ---------------------------------------------------------------------------

def test_list_feedbacks_success(client, sample_feedback):
    """GET /admin/feedbacks should return list of feedbacks with stats."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock query for feedbacks list
        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_feedback]
        mock_db.query.return_value = mock_query

        # Mock queries for statistics
        mock_db.query.return_value.filter.return_value.count.side_effect = [5, 2]  # positive=5, negative=2

        resp = client.get("/api/admin/feedbacks")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["statistics"]["positive_count"] == 5
    assert data["statistics"]["negative_count"] == 2
    assert data["statistics"]["total_count"] == 7


def test_list_feedbacks_with_filter(client, sample_feedback):
    """GET /admin/feedbacks should filter by session_id and feedback_type."""
    with patch("app.api.admin.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.count.return_value = 1
        mock_query.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_feedback]
        mock_db.query.return_value = mock_query

        # Mock for statistics
        mock_db.query.return_value.filter.return_value.count.side_effect = [1, 0]

        resp = client.get("/api/admin/feedbacks?session_id=session-1&feedback_type=positive")

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Feedback Submission Tests (Chat API)
# ---------------------------------------------------------------------------

def test_submit_feedback_positive(client):
    """POST /chat/sessions/{id}/messages/{index}/feedback should create positive feedback."""
    with patch("app.api.chat.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing feedback

        resp = client.post(
            "/api/chat/sessions/session-1/messages/0/feedback",
            json={"feedback_type": "positive"}
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "created"
    assert data["feedback_type"] == "positive"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_submit_feedback_negative(client):
    """POST /chat/sessions/{id}/messages/{index}/feedback should create negative feedback."""
    with patch("app.api.chat.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.post(
            "/api/chat/sessions/session-1/messages/0/feedback",
            json={"feedback_type": "negative"}
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "created"
    assert data["feedback_type"] == "negative"


def test_submit_feedback_update_existing(client):
    """POST feedback should update existing feedback."""
    existing_feedback = ChatFeedback(
        id="fb-1",
        session_id="session-1",
        message_index=0,
        feedback_type="positive",
        user_id="test-admin-id",
        created_at=datetime.utcnow(),
    )

    with patch("app.api.chat.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = existing_feedback

        resp = client.post(
            "/api/chat/sessions/session-1/messages/0/feedback",
            json={"feedback_type": "negative"}
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "updated"
    assert data["feedback_type"] == "negative"


def test_submit_feedback_invalid_type(client):
    """POST feedback should reject invalid feedback_type."""
    resp = client.post(
        "/api/chat/sessions/session-1/messages/0/feedback",
        json={"feedback_type": "invalid"}
    )

    assert resp.status_code == 400
    assert "must be 'positive' or 'negative'" in resp.json()["detail"]
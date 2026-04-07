"""
Tests for Chat API — Property 10 (流式输出格式) + 历史记录接口单元测试.
Feature: qa-copilot
  Property 10: 流式输出格式
  Task 12.2: SSE Content-Type 与事件格式
  Task 12.3: 历史消息接口字段完整性
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.schemas import Message, SourceRef


@pytest.fixture
def client(override_auth):
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_rag(tokens: list[str] | None = None, sources: list[dict] | None = None):
    """Return a mock RAGService whose answer() yields tokens then a sources event."""
    tokens = tokens or ["Hello", " world"]
    sources = sources or []

    async def _answer(session_id, question):
        for t in tokens:
            yield t
        if sources:
            yield {"type": "sources", "data": sources}

    mock = MagicMock()
    mock.answer = _answer
    return mock


def _make_mock_conv(messages: list[Message] | None = None):
    """Return a mock ConversationManager with preset messages."""
    messages = messages or []
    mock = MagicMock()
    mock.list_sessions.return_value = []
    mock.get_or_create_session.return_value = MagicMock()
    mock.delete_session.return_value = None
    mock.clear_history.return_value = None
    mock.get_recent_history.return_value = messages
    return mock


# ---------------------------------------------------------------------------
# Property 10: 流式输出格式
# Validates: Requirements 3.6
# ---------------------------------------------------------------------------

def test_sse_content_type(client):
    """POST /messages must respond with Content-Type: text/event-stream."""
    mock_rag = _make_mock_rag()
    mock_conv = _make_mock_conv()

    with patch("app.api.chat._copilot_service", mock_rag), \
         patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.post(
            "/api/chat/sessions/test-session/messages",
            json={"question": "hello"},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


def test_sse_events_start_with_data(client):
    """Every SSE line must start with 'data:'."""
    mock_rag = _make_mock_rag(tokens=["Hi", " there"])
    mock_conv = _make_mock_conv()

    with patch("app.api.chat._copilot_service", mock_rag), \
         patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.post(
            "/api/chat/sessions/s1/messages",
            json={"question": "test"},
        )

    non_empty_lines = [l for l in resp.text.splitlines() if l.strip()]
    for line in non_empty_lines:
        assert line.startswith("data:"), f"Line does not start with 'data:': {line!r}"


def test_sse_token_events_have_type_and_content(client):
    """Token events must have type='token' and a content field."""
    mock_rag = _make_mock_rag(tokens=["chunk1", "chunk2"])
    mock_conv = _make_mock_conv()

    with patch("app.api.chat._copilot_service", mock_rag), \
         patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.post(
            "/api/chat/sessions/s1/messages",
            json={"question": "test"},
        )

    token_events = []
    for line in resp.text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        data = json.loads(payload)
        if data.get("type") == "token":
            token_events.append(data)

    assert len(token_events) == 2
    for ev in token_events:
        assert "content" in ev


def test_sse_ends_with_done(client):
    """SSE stream must end with 'data: [DONE]'."""
    mock_rag = _make_mock_rag(tokens=["x"])
    mock_conv = _make_mock_conv()

    with patch("app.api.chat._copilot_service", mock_rag), \
         patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.post(
            "/api/chat/sessions/s1/messages",
            json={"question": "q"},
        )

    non_empty = [l.strip() for l in resp.text.splitlines() if l.strip()]
    assert non_empty[-1] == "data: [DONE]"


def test_sse_sources_event_format(client):
    """Sources event must have type='sources' and a data list."""
    src = {"doc_id": "d1", "filename": "doc.pdf", "chunk_position": 0}
    mock_rag = _make_mock_rag(tokens=["answer"], sources=[src])
    mock_conv = _make_mock_conv()

    with patch("app.api.chat._copilot_service", mock_rag), \
         patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.post(
            "/api/chat/sessions/s1/messages",
            json={"question": "q"},
        )

    sources_events = []
    for line in resp.text.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        data = json.loads(payload)
        if data.get("type") == "sources":
            sources_events.append(data)

    assert len(sources_events) == 1
    assert isinstance(sources_events[0]["data"], list)
    assert sources_events[0]["data"][0]["filename"] == "doc.pdf"


# ---------------------------------------------------------------------------
# Task 12.3: 历史记录接口字段完整性
# Validates: Requirements 4.6
# ---------------------------------------------------------------------------

def test_get_messages_returns_list(client):
    """GET /sessions/{id}/messages must return a list."""
    mock_conv = _make_mock_conv(messages=[])

    with patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.get("/api/chat/sessions/s1/messages")

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_messages_fields_complete(client):
    """Each message must have role, content, timestamp, sources fields."""
    msgs = [
        Message(role="user", content="What is RAG?", timestamp=datetime.utcnow()),
        Message(
            role="assistant",
            content="RAG stands for...",
            timestamp=datetime.utcnow(),
            sources=[SourceRef(doc_id="d1", filename="doc.pdf", chunk_position=2)],
        ),
    ]
    mock_conv = _make_mock_conv(messages=msgs)

    with patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.get("/api/chat/sessions/s1/messages")

    data = resp.json()
    assert len(data) == 2
    for msg in data:
        assert "role" in msg
        assert "content" in msg
        assert "timestamp" in msg
        assert "sources" in msg


def test_get_messages_source_fields(client):
    """Source refs in messages must have doc_id, filename, chunk_position."""
    msgs = [
        Message(
            role="assistant",
            content="answer",
            timestamp=datetime.utcnow(),
            sources=[SourceRef(doc_id="doc-1", filename="report.pdf", chunk_position=5)],
        )
    ]
    mock_conv = _make_mock_conv(messages=msgs)

    with patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.get("/api/chat/sessions/s1/messages")

    src = resp.json()[0]["sources"][0]
    assert src["doc_id"] == "doc-1"
    assert src["filename"] == "report.pdf"
    assert src["chunk_position"] == 5


def test_get_messages_hydrates_missing_source_content_from_vector_store(client):
    msgs = [
        Message(
            role="assistant",
            content="answer",
            timestamp=datetime.utcnow(),
            sources=[SourceRef(doc_id="doc-1", filename="report.pdf", chunk_position=5, content=None)],
        )
    ]
    mock_conv = _make_mock_conv(messages=msgs)
    mock_vector_store = MagicMock()
    mock_vector_store.get_chunk_content.return_value = "chunk body"
    mock_retriever = MagicMock()
    mock_retriever._vector_store = mock_vector_store
    mock_rag = MagicMock()
    mock_rag._retriever = mock_retriever

    with patch("app.api.chat._conversation_manager", mock_conv), \
         patch("app.api.chat._copilot_service", mock_rag):
        resp = client.get("/api/chat/sessions/s1/messages")

    src = resp.json()[0]["sources"][0]
    assert src["content"] == "chunk body"
    mock_vector_store.get_chunk_content.assert_called_once_with("doc-1", 5, "report.pdf")


def test_get_messages_empty_session(client):
    """GET /messages on a session with no history returns empty list."""
    mock_conv = _make_mock_conv(messages=[])

    with patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.get("/api/chat/sessions/nonexistent/messages")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_messages_role_values(client):
    """Message roles must be 'user' or 'assistant'."""
    msgs = [
        Message(role="user", content="q", timestamp=datetime.utcnow()),
        Message(role="assistant", content="a", timestamp=datetime.utcnow()),
    ]
    mock_conv = _make_mock_conv(messages=msgs)

    with patch("app.api.chat._conversation_manager", mock_conv):
        resp = client.get("/api/chat/sessions/s1/messages")

    roles = [m["role"] for m in resp.json()]
    assert roles == ["user", "assistant"]

"""
Tests for ConversationManager — Property 11, 12, 13.
Feature: internal-knowledge-base
  Property 11: Session 隔离性
  Property 12: Session 生命周期
  Property 13: 清除历史往返
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.schemas import Message, Session
from app.services.conversation import ConversationManager, _messages_to_json, _messages_from_json


# ---------------------------------------------------------------------------
# Fixture: in-memory ConversationManager (no real DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr():
    """ConversationManager with SQLite operations mocked out."""
    with patch("app.services.conversation.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = None  # no existing sessions
        mock_db.query.return_value.order_by.return_value.all.return_value = []

        manager = ConversationManager()
        # Patch _load_from_db to always return None (no persistence)
        manager._load_from_db = MagicMock(return_value=None)
        manager._persist_session = MagicMock()
        manager._persist_last_active = MagicMock()
        manager._create_in_db = MagicMock(side_effect=lambda sid, now, uid=None: Session(
            session_id=sid, title="新对话", messages=[], created_at=now, last_active=now
        ))
        yield manager


def _sid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Property 11: Session 隔离性
# Validates: Requirements 4.1
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 11: Session 隔离性
def test_session_isolation_messages_do_not_bleed(mgr):
    """Adding a message to session A must not affect session B."""
    sid_a = _sid()
    sid_b = _sid()

    mgr.get_or_create_session(sid_a)
    mgr.get_or_create_session(sid_b)

    mgr.add_message(sid_a, "user", "Hello from A")
    mgr.add_message(sid_a, "assistant", "Reply from A")

    history_b = mgr.get_recent_history(sid_b)
    assert len(history_b) == 0


# Feature: internal-knowledge-base, Property 11: Session 隔离性
@given(
    st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
    st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
)
@settings(max_examples=30)
def test_session_isolation_property(messages_a: list[str], messages_b: list[str]):
    """For any two sessions, messages added to one never appear in the other."""
    with patch("app.services.conversation.SessionLocal"), \
         patch("app.services.conversation.ChatSession"):
        manager = ConversationManager()
        manager._load_from_db = MagicMock(return_value=None)
        manager._persist_session = MagicMock()
        manager._persist_last_active = MagicMock()
        now = datetime.utcnow()
        manager._create_in_db = MagicMock(side_effect=lambda sid, t: Session(
            session_id=sid, title="新对话", messages=[], created_at=t, last_active=t
        ))

        sid_a = _sid()
        sid_b = _sid()

        for msg in messages_a:
            manager.add_message(sid_a, "user", msg)

        for msg in messages_b:
            manager.add_message(sid_b, "user", msg)

        history_a = manager.get_recent_history(sid_a, 100)
        history_b = manager.get_recent_history(sid_b, 100)

        assert len(history_a) == len(messages_a)
        assert len(history_b) == len(messages_b)
        assert all(m.content in messages_a for m in history_a)
        assert all(m.content in messages_b for m in history_b)


# ---------------------------------------------------------------------------
# Property 12: Session 生命周期
# Validates: Requirements 4.3, 4.5
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 12: Session 生命周期
def test_session_history_accessible_before_timeout(mgr):
    """History is accessible while session is active (not expired)."""
    sid = _sid()
    mgr.add_message(sid, "user", "question")
    history = mgr.get_recent_history(sid)
    assert len(history) == 1


# Feature: internal-knowledge-base, Property 12: Session 生命周期
def test_session_expired_after_cleanup(mgr):
    """After cleanup_expired, sessions older than timeout are removed from cache."""
    sid = _sid()
    mgr.get_or_create_session(sid)
    mgr.add_message(sid, "user", "old message")

    # Manually backdate last_active
    mgr._cache[sid].last_active = datetime.utcnow() - timedelta(minutes=31)

    mgr.cleanup_expired(timeout_minutes=30)

    assert sid not in mgr._cache


def test_active_session_not_expired_by_cleanup(mgr):
    """Sessions active within timeout window are NOT removed by cleanup."""
    sid = _sid()
    mgr.add_message(sid, "user", "recent message")
    # last_active is now — should survive cleanup
    mgr.cleanup_expired(timeout_minutes=30)
    assert sid in mgr._cache


# ---------------------------------------------------------------------------
# Property 13: 清除历史往返
# Validates: Requirements 4.4
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 13: 清除历史往返
def test_clear_history_empties_messages(mgr):
    """After clear_history, the session's message list is empty."""
    sid = _sid()
    mgr.add_message(sid, "user", "msg 1")
    mgr.add_message(sid, "assistant", "reply 1")
    mgr.add_message(sid, "user", "msg 2")

    mgr.clear_history(sid)

    history = mgr.get_recent_history(sid)
    assert history == []


# Feature: internal-knowledge-base, Property 13: 清除历史往返
@given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20))
@settings(max_examples=30)
def test_clear_history_property(messages: list[str]):
    """For any session with N messages, clear_history results in 0 messages."""
    with patch("app.services.conversation.SessionLocal"), \
         patch("app.services.conversation.ChatSession"):
        manager = ConversationManager()
        manager._load_from_db = MagicMock(return_value=None)
        manager._persist_session = MagicMock()
        manager._persist_last_active = MagicMock()
        manager._create_in_db = MagicMock(side_effect=lambda sid, t: Session(
            session_id=sid, title="新对话", messages=[], created_at=t, last_active=t
        ))

        sid = _sid()
        for msg in messages:
            manager.add_message(sid, "user", msg)

        manager.clear_history(sid)
        history = manager.get_recent_history(sid, 100)
        assert history == []


def test_new_messages_after_clear_start_from_index_zero(mgr):
    """After clearing, new messages are accessible and start fresh."""
    sid = _sid()
    mgr.add_message(sid, "user", "old")
    mgr.clear_history(sid)
    mgr.add_message(sid, "user", "new message")

    history = mgr.get_recent_history(sid)
    assert len(history) == 1
    assert history[0].content == "new message"


# ---------------------------------------------------------------------------
# Message serialization helpers
# ---------------------------------------------------------------------------

def test_messages_json_roundtrip():
    """_messages_to_json / _messages_from_json are inverse operations."""
    messages = [
        Message(role="user", content="hello", timestamp=datetime(2024, 1, 1, 12, 0, 0)),
        Message(role="assistant", content="world", timestamp=datetime(2024, 1, 1, 12, 0, 1)),
    ]
    restored = _messages_from_json(_messages_to_json(messages))
    assert len(restored) == 2
    assert restored[0].role == "user"
    assert restored[0].content == "hello"
    assert restored[1].role == "assistant"


def test_get_recent_history_respects_n_limit(mgr):
    """get_recent_history(n) returns at most n messages."""
    sid = _sid()
    for i in range(15):
        mgr.add_message(sid, "user", f"msg {i}")

    history = mgr.get_recent_history(sid, n=10)
    assert len(history) == 10
    # Should be the last 10
    assert history[-1].content == "msg 14"

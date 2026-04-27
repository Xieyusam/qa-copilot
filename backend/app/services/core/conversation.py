"""
ConversationManager: SQLite 持久化的多轮对话 Session 管理器，内存缓存加速。
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from app.core.schemas import Message, Session, SourceRef
from app.db.session import SessionLocal
from app.models.document import ChatSession


def _messages_to_json(messages: list[Message]) -> str:
    def _src(s: SourceRef) -> dict:
        return {
            "doc_id": s.doc_id,
            "filename": s.filename,
            "chunk_position": s.chunk_position,
            "similarity_score": getattr(s, "similarity_score", None),
            "content": getattr(s, "content", None)
        }

    rows = []
    for m in messages:
        rows.append({
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
            "sources": [_src(s) for s in (m.sources or [])],
            "additional_kwargs": m.additional_kwargs,
        })
    return json.dumps(rows, ensure_ascii=False)


def _messages_from_json(raw: str) -> list[Message]:
    rows = json.loads(raw)
    result = []
    for r in rows:
        sources = []
        for s in (r.get("sources") or []):
            sources.append(
                SourceRef(
                    doc_id=s.get("doc_id", ""),
                    filename=s.get("filename", ""),
                    chunk_position=s.get("chunk_position", 0),
                    similarity_score=s.get("similarity_score"),
                    content=s.get("content")
                )
            )
        result.append(Message(
            role=r["role"],
            content=r["content"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            sources=sources or None,
            additional_kwargs=r.get("additional_kwargs"),
        ))
    return result


class ConversationManager:
    """SQLite 持久化 + 内存缓存的 Session 管理器。"""

    def __init__(self) -> None:
        self._cache: dict[str, Session] = {}
        self._lock = threading.Lock()

        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True, name="conversation-cleanup"
        )
        self._cleanup_thread.start()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def get_or_create_session(self, session_id: str, user_id: str | None = None) -> Session:
        now = datetime.utcnow()
        with self._lock:
            if session_id in self._cache:
                self._cache[session_id].last_active = now
                self._persist_last_active(session_id, now)
                return self._cache[session_id]

        # 尝试从 DB 加载
        session = self._load_from_db(session_id)
        if session is None:
            session = self._create_in_db(session_id, now, user_id)

        with self._lock:
            self._cache[session_id] = session
        return session

    def list_sessions(self, user_id: str | None = None) -> list[dict]:
        """返回当前用户的 Session 元数据，按 last_active 倒序。"""
        db = SessionLocal()
        try:
            query = db.query(ChatSession)
            if user_id:
                query = query.filter(ChatSession.user_id == user_id)
            rows = query.order_by(ChatSession.last_active.desc()).all()
            return [
                {
                    "session_id": r.id,
                    "title": r.title,
                    "created_at": r.created_at.isoformat(),
                    "last_active": r.last_active.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[SourceRef] | None = None,
        additional_kwargs: dict[str, Any] | None = None,
    ) -> Message:
        now = datetime.utcnow()
        message = Message(role=role, content=content, timestamp=now, sources=sources, additional_kwargs=additional_kwargs)
        with self._lock:
            session = self._get_or_create_locked(session_id, now)
            session.messages.append(message)
            session.last_active = now
            # 首条用户消息作为标题
            if role == "user" and len([m for m in session.messages if m.role == "user"]) == 1:
                session.title = content[:20]
            self._persist_session(session)
        return message

    def get_recent_history(self, session_id: str, n: int = 10) -> list[Message]:
        with self._lock:
            session = self._cache.get(session_id)
        if session is None:
            session = self._load_from_db(session_id)
            if session is None:
                return []
            with self._lock:
                self._cache[session_id] = session
        return list(session.messages[-n:])

    def clear_history(self, session_id: str) -> None:
        now = datetime.utcnow()
        with self._lock:
            session = self._cache.get(session_id)
            if session is not None:
                session.messages = []
                session.last_active = now
            # 统一在锁内持久化，避免缓存与 DB 双写竞态
            db = SessionLocal()
            try:
                row = db.get(ChatSession, session_id)
                if row:
                    row.messages_json = "[]"
                    row.last_active = now
                    db.commit()
            finally:
                db.close()

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._cache.pop(session_id, None)
        db = SessionLocal()
        try:
            row = db.get(ChatSession, session_id)
            if row:
                db.delete(row)
                db.commit()
        finally:
            db.close()

    def cleanup_expired(self, timeout_minutes: int = 30) -> None:
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        with self._lock:
            expired = [sid for sid, s in self._cache.items() if s.last_active < cutoff]
            for sid in expired:
                del self._cache[sid]

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _load_from_db(self, session_id: str) -> Session | None:
        db = SessionLocal()
        try:
            row = db.get(ChatSession, session_id)
            if row is None:
                return None
            return Session(
                session_id=row.id,
                title=row.title,
                messages=_messages_from_json(row.messages_json),
                created_at=row.created_at,
                last_active=row.last_active,
            )
        finally:
            db.close()

    def _create_in_db(self, session_id: str, now: datetime, user_id: str | None = None) -> Session:
        db = SessionLocal()
        try:
            row = ChatSession(id=session_id, title="新对话", messages_json="[]", created_at=now, last_active=now, user_id=user_id)
            db.add(row)
            db.commit()
        finally:
            db.close()
        return Session(session_id=session_id, title="新对话", messages=[], created_at=now, last_active=now)

    def _persist_session(self, session: Session) -> None:
        db = SessionLocal()
        try:
            row = db.get(ChatSession, session.session_id)
            if row is None:
                row = ChatSession(id=session.session_id)
                db.add(row)
            row.title = session.title
            row.messages_json = _messages_to_json(session.messages)
            row.last_active = session.last_active
            db.commit()
        finally:
            db.close()

    def _persist_last_active(self, session_id: str, now: datetime) -> None:
        db = SessionLocal()
        try:
            row = db.get(ChatSession, session_id)
            if row:
                row.last_active = now
                db.commit()
        finally:
            db.close()

    def _get_or_create_locked(self, session_id: str, now: datetime) -> Session:
        if session_id not in self._cache:
            session = self._load_from_db(session_id)
            if session is None:
                session = Session(session_id=session_id, title="新对话", messages=[], created_at=now, last_active=now)
            self._cache[session_id] = session
        return self._cache[session_id]

    def _background_cleanup(self) -> None:
        while True:
            time.sleep(5 * 60)
            try:
                self.cleanup_expired(30)
            except Exception:
                pass

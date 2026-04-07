"""
Chat API routes — Session management and SSE streaming Q&A.
Prefix is set in main.py (e.g. /api/chat).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.db.session import SessionLocal
from app.models.user import User
from app.models.feedback import ChatFeedback
from app.services.conversation import ConversationManager
from app.services.copilot_service import CopilotService

logger = logging.getLogger(__name__)

router = APIRouter()

_conversation_manager: ConversationManager | None = None
_copilot_service: CopilotService | None = None

def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager

def get_copilot_service() -> CopilotService:
    global _copilot_service
    if _copilot_service is None:
        _copilot_service = CopilotService(conversation_manager=get_conversation_manager())
    return _copilot_service


class MessageRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# GET /sessions — 获取 Session 列表
# ---------------------------------------------------------------------------

@router.get("/sessions")
@router.get("/sessions/")
def list_sessions(current_user: User = Depends(get_current_user)):
    return get_conversation_manager().list_sessions(user_id=current_user.id)


# ---------------------------------------------------------------------------
# POST /sessions — 创建新 Session
# ---------------------------------------------------------------------------

@router.post("/sessions", status_code=201)
def create_session(current_user: User = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    get_conversation_manager().get_or_create_session(session_id, user_id=current_user.id)
    return {"session_id": session_id}


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id} — 删除 Session
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    get_conversation_manager().delete_session(session_id)


# ---------------------------------------------------------------------------
# POST /sessions/{session_id}/messages — 发送消息（SSE 流式响应）
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: MessageRequest, current_user: User = Depends(get_current_user)):
    # 确保 session 存在，如果是新发送则绑定到当前用户
    get_conversation_manager().get_or_create_session(session_id, user_id=current_user.id)
    
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for chunk in get_copilot_service().answer(session_id, body.question):
                if isinstance(chunk, dict) and chunk.get("type") == "sources":
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                else:
                    payload = json.dumps(
                        {"type": "token", "content": chunk}, ensure_ascii=False
                    )
                    yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.exception("Error during SSE stream for session %s", session_id)
            error_payload = json.dumps({"type": "error", "content": str(exc)})
            yield f"data: {error_payload}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id}/history — 清除对话历史
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}/history")
def clear_history(session_id: str, current_user: User = Depends(get_current_user)):
    get_conversation_manager().clear_history(session_id)
    return {"status": "cleared"}


# ---------------------------------------------------------------------------
# GET /sessions/{session_id}/messages — 获取历史消息
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, current_user: User = Depends(get_current_user)):
    messages = get_conversation_manager().get_recent_history(session_id, 100)
    vector_store = getattr(getattr(get_copilot_service(), "_retriever", None), "_vector_store", None)
    result = []
    for msg in messages:
        sources = []
        for s in (msg.sources or []):
            content = getattr(s, "content", None)
            if not content and vector_store is not None:
                content = vector_store.get_chunk_content(
                    s.doc_id, s.chunk_position, s.filename
                )
            resolved_content = content if isinstance(content, str) else ""
            sources.append(
                {
                    "doc_id": s.doc_id,
                    "filename": s.filename,
                    "chunk_position": s.chunk_position,
                    "similarity_score": s.similarity_score,
                    "content": resolved_content,
                }
            )
        result.append(
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "sources": sources,
            }
        )
    return result


# ---------------------------------------------------------------------------
# POST /sessions/{session_id}/messages/{message_index}/feedback — 提交反馈
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    feedback_type: str  # "positive" or "negative"


@router.post("/sessions/{session_id}/messages/{message_index}/feedback", status_code=201)
def submit_feedback(
    session_id: str,
    message_index: int,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit feedback (positive/negative) for a specific AI message."""
    if body.feedback_type not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="feedback_type must be 'positive' or 'negative'")

    db = SessionLocal()
    try:
        # Check if feedback already exists for this message
        existing = db.query(ChatFeedback).filter(
            ChatFeedback.session_id == session_id,
            ChatFeedback.message_index == message_index,
            ChatFeedback.user_id == current_user.id,
        ).first()

        if existing:
            # Update existing feedback
            existing.feedback_type = body.feedback_type
            db.commit()
            return {"status": "updated", "feedback_type": body.feedback_type}

        # Create new feedback
        feedback = ChatFeedback(
            session_id=session_id,
            message_index=message_index,
            feedback_type=body.feedback_type,
            user_id=current_user.id,
        )
        db.add(feedback)
        db.commit()
        return {"status": "created", "feedback_type": body.feedback_type}
    finally:
        db.close()

"""
Chat API routes — Session management and SSE streaming Q&A.
Prefix is set in main.py (e.g. /api/chat).
"""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.feedback import ChatFeedback
from app.services.core.conversation import ConversationManager
from app.services.core.copilot_service import CopilotService
from app.db.session import SessionLocal
from app.services.observability.logger import get_logger
from app.services.document.parser import DocumentParser

logger = get_logger(__name__)

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

class AttachmentRef(BaseModel):
    id: str
    filename: str
    size: int


@router.post("/sessions/{session_id}/messages")
async def send_message(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    # 解析 JSON body
    body = await request.json()
    q = body.get("question", "") if isinstance(body, dict) else ""

    # 防御：question 不能为空
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="问题内容不能为空")

    # 获取附件引用
    attachments: list[AttachmentRef] = []
    raw_attachments = body.get("attachments", [])
    if raw_attachments:
        for att in raw_attachments:
            attachments.append(AttachmentRef(
                id=att.get("id", ""),
                filename=att.get("filename", "unknown"),
                size=att.get("size", 0),
            ))

    # 确保 session 存在，如果是新发送则绑定到当前用户
    get_conversation_manager().get_or_create_session(session_id, user_id=current_user.id)

    # 准备附件列表（传给 answer 存入消息历史，middleware 负责内容注入）
    att_list = [att.model_dump() for att in attachments] if attachments else None
    logger.info(f"[chat] attachments count: {len(attachments) if attachments else 0}, att_list: {att_list}")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for chunk in get_copilot_service().answer(session_id, q, attachments=att_list):
                if not isinstance(chunk, dict):
                    # 字符串类型，作为 token 处理
                    payload = json.dumps(
                        {"type": "token", "content": str(chunk)}, ensure_ascii=False
                    )
                    yield f"data: {payload}\n\n"
                elif chunk.get("type") == "sources":
                    # 来源信息
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                elif chunk.get("type") in ("status", "token", "done", "error"):
                    # 直接透传已知类型
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                else:
                    # 未知类型，作为 token 处理
                    payload = json.dumps(
                        {"type": "token", "content": str(chunk)}, ensure_ascii=False
                    )
                    yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.exception("Error during SSE stream for session %s", session_id)
            error_payload = json.dumps({"type": "error", "content": str(exc)})
            yield f"data: {error_payload}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _read_attachments(attachments: list[AttachmentRef]) -> list[str]:
    """根据 attachment_id 读取文件并解析内容。"""
    from pathlib import Path
    from app.config import settings

    results = []
    attachments_dir = Path(settings.attachments_dir)

    for att in attachments:
        # 查找文件
        filepath = None
        for p in attachments_dir.glob(f"{att.id}_*"):
            filepath = p
            break

        if not filepath or not filepath.exists():
            results.append(f"【文件: {att.filename}】\n[文件不存在]")
            continue

        ext = filepath.suffix.lower().lstrip(".")
        try:
            if ext in ("pdf", "docx", "xlsx", "xls"):
                parsed = DocumentParser().parse(str(filepath), ext, doc_id=None)
                text = parsed.content[:8000]
                results.append(f"【文件: {att.filename}】\n{text}")
            else:
                # 纯文本直接解码
                content = filepath.read_text(encoding="utf-8")
                results.append(f"【文件: {att.filename}】\n{content[:8000]}")
        except Exception as e:
            results.append(f"【文件: {att.filename}】\n[解析失败: {str(e)}]")

    return results


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

    # 预先查询该用户在该 session 的所有 feedback
    db = SessionLocal()
    feedbacks = {}
    try:
        rows = db.query(ChatFeedback).filter(
            ChatFeedback.session_id == session_id,
            ChatFeedback.user_id == current_user.id,
        ).all()
        # key: message_index, value: feedback_type
        for fb in rows:
            feedbacks[fb.message_index] = fb.feedback_type
    finally:
        db.close()

    result = []
    # 计算 assistant 消息的索引（用于匹配 feedback）
    assistant_index = 0
    for idx, msg in enumerate(messages):
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

        # 只有 assistant 消息才有 feedback
        feedback_type = None
        if msg.role == "assistant":
            feedback_type = feedbacks.get(assistant_index)
            assistant_index += 1

        result.append(
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "sources": sources,
                "attachments": msg.additional_kwargs.get("attachments") if msg.additional_kwargs else None,
                "feedback_type": feedback_type,
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

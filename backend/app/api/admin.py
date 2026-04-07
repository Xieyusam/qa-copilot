"""
Admin API routes for observability and feedback management.
Prefix is set in main.py (e.g. /api/admin).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import require_admin
from app.db.session import SessionLocal
from app.models.trace import AgentTrace, TraceStep
from app.models.feedback import ChatFeedback

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /traces — 获取追踪列表
# ---------------------------------------------------------------------------

@router.get("/traces")
@router.get("/traces/")
def list_traces(
    page: int = 1,
    page_size: int = 20,
    session_id: str | None = None,
    _: None = Depends(require_admin)
):
    """Get list of agent execution traces with pagination."""
    db = SessionLocal()
    try:
        query = db.query(AgentTrace)
        if session_id:
            query = query.filter(AgentTrace.session_id == session_id)

        total = query.count()
        traces = query.order_by(AgentTrace.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": t.id,
                    "session_id": t.session_id,
                    "question": t.question[:200] if t.question else None,  # Truncate
                    "final_answer": t.final_answer[:200] if t.final_answer else None,
                    "total_time_ms": round(t.total_time_ms, 2),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "steps_count": len(t.steps) if t.steps else 0,
                }
                for t in traces
            ]
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /traces/{trace_id} — 获取单次追踪详情
# ---------------------------------------------------------------------------

@router.get("/traces/{trace_id}")
def get_trace_detail(trace_id: str, _: None = Depends(require_admin)):
    """Get detailed information for a single trace."""
    db = SessionLocal()
    try:
        trace = db.get(AgentTrace, trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        return {
            "id": trace.id,
            "session_id": trace.session_id,
            "question": trace.question,
            "final_answer": trace.final_answer,
            "total_time_ms": round(trace.total_time_ms, 2),
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
            "steps": [
                {
                    "id": s.id,
                    "step_index": s.step_index,
                    "step_type": s.step_type,
                    "tool_name": s.tool_name,
                    "input_prompt": s.input_prompt,
                    "output_result": s.output_result,
                    "time_ms": round(s.time_ms, 2),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sorted(trace.steps, key=lambda x: x.step_index)
            ]
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /traces/{trace_id}/export — 导出追踪数据为 JSON
# ---------------------------------------------------------------------------

@router.get("/traces/{trace_id}/export")
def export_trace(trace_id: str, _: None = Depends(require_admin)):
    """Export a single trace as downloadable JSON."""
    db = SessionLocal()
    try:
        trace = db.get(AgentTrace, trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        data = {
            "id": trace.id,
            "session_id": trace.session_id,
            "question": trace.question,
            "final_answer": trace.final_answer,
            "total_time_ms": round(trace.total_time_ms, 2),
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
            "steps": [
                {
                    "id": s.id,
                    "step_index": s.step_index,
                    "step_type": s.step_type,
                    "tool_name": s.tool_name,
                    "input_prompt": s.input_prompt,
                    "output_result": s.output_result,
                    "time_ms": round(s.time_ms, 2),
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sorted(trace.steps, key=lambda x: x.step_index)
            ]
        }

        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": f"attachment; filename=trace_{trace_id}.json"
            }
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /feedbacks — 获取反馈统计
# ---------------------------------------------------------------------------

@router.get("/feedbacks")
@router.get("/feedbacks/")
def list_feedbacks(
    page: int = 1,
    page_size: int = 20,
    session_id: str | None = None,
    feedback_type: str | None = None,
    _: None = Depends(require_admin)
):
    """Get list of chat feedbacks with pagination."""
    db = SessionLocal()
    try:
        query = db.query(ChatFeedback)
        if session_id:
            query = query.filter(ChatFeedback.session_id == session_id)
        if feedback_type:
            query = query.filter(ChatFeedback.feedback_type == feedback_type)

        total = query.count()
        feedbacks = query.order_by(ChatFeedback.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        # Get statistics
        positive_count = db.query(ChatFeedback).filter(ChatFeedback.feedback_type == "positive").count()
        negative_count = db.query(ChatFeedback).filter(ChatFeedback.feedback_type == "negative").count()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "statistics": {
                "positive_count": positive_count,
                "negative_count": negative_count,
                "total_count": positive_count + negative_count,
            },
            "items": [
                {
                    "id": f.id,
                    "session_id": f.session_id,
                    "message_index": f.message_index,
                    "feedback_type": f.feedback_type,
                    "user_id": f.user_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in feedbacks
            ]
        }
    finally:
        db.close()
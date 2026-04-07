"""
Agent execution trace models for observability.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class AgentTrace(Base):
    """Records a complete Agent execution trace for a single conversation turn."""
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to trace steps
    steps: Mapped[list["TraceStep"]] = relationship("TraceStep", back_populates="trace", cascade="all, delete-orphan")


class TraceStep(Base):
    """Records a single step in the Agent execution (e.g., tool call, LLM stream)."""
    __tablename__ = "trace_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id: Mapped[str] = mapped_column(String, ForeignKey("agent_traces.id"), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "tool_call", "llm_stream", "tool_result"
    tool_name: Mapped[str | None] = mapped_column(String, nullable=True)
    input_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship back to parent trace
    trace: Mapped["AgentTrace"] = relationship("AgentTrace", back_populates="steps")
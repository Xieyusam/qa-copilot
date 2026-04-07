"""
Chat feedback model for recording user satisfaction with AI responses.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class ChatFeedback(Base):
    """Records user feedback (positive/negative) for a specific AI response."""
    __tablename__ = "chat_feedbacks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("chat_sessions.id"), nullable=False)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Index of the AI message in the session
    feedback_type: Mapped[str] = mapped_column(String, nullable=False)  # "positive" or "negative"
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
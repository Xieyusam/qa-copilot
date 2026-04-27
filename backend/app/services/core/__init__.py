"""核心服务"""
from app.services.core.copilot_service import CopilotService
from app.services.core.conversation import ConversationManager

__all__ = ["CopilotService", "ConversationManager"]

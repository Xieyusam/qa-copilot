"""
LLMClient — wraps LangChain ChatOpenAI with streaming and retry logic.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}

MAX_RETRIES = 3
TIMEOUT_SECONDS = 30


class LLMClient:
    """Async streaming LLM client backed by LangChain ChatOpenAI."""

    # Use class-level variable for singleton
    _instance: ChatOpenAI | None = None

    def __init__(self) -> None:
        if LLMClient._instance is None:
            LLMClient._instance = ChatOpenAI(
                base_url=settings.llm_api_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                streaming=True,
                timeout=TIMEOUT_SECONDS,
            )
        # 统一使用 self.model，对外暴露和内部调用共用
        self.model = LLMClient._instance

    async def chat(self, messages: list[dict], max_tokens: int | None = None) -> str:
        """Non-streaming chat completion.

        Args:
            messages: List of dicts with 'role' and 'content' keys.
            max_tokens: Optional limit on the number of tokens to generate.

        Returns:
            The complete response text.
        """
        lc_messages = [
            _ROLE_MAP.get(msg["role"], HumanMessage)(content=msg["content"])
            for msg in messages
        ]
        
        # Determine kwargs for invoke
        kwargs = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
            
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.model.ainvoke(lc_messages, **kwargs)
                return response.content
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "LLM chat attempt %d/%d failed: %s. Retrying in %ds.",
                        attempt + 1,
                        MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("LLM chat failed after %d attempts: %s", MAX_RETRIES, exc)
                    raise last_exc

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream chat completion tokens.

        Args:
            messages: List of dicts with 'role' and 'content' keys.

        Yields:
            Text chunks as they arrive from the LLM.
        """
        lc_messages = [
            _ROLE_MAP.get(msg["role"], HumanMessage)(content=msg["content"])
            for msg in messages
        ]

        last_exc: Exception | None = None
        # 重试仅对首次连接失败有效，流式传输中断后无法重试（已消费部分数据）
        for attempt in range(MAX_RETRIES):
            try:
                async for chunk in self.model.astream(lc_messages):
                    text = chunk.content
                    if text:
                        yield text
                return  # success — exit generator
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        "LLM stream attempt %d/%d failed: %s. Retrying in %ds.",
                        attempt + 1,
                        MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("LLM stream failed after %d attempts: %s", MAX_RETRIES, exc)
                    raise last_exc

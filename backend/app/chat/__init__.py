"""Composition helper for the chat service (used by app.main)."""

from __future__ import annotations

from typing import Any

from app.db import ChatRepository
from app.llm import (
    ChatService,
    LiteLLMClient,
    LLMClient,
    MockLLMClient,
    TradingServiceAdapter,
    build_default_handlers,
)


def create_chat_service(
    *, trading: Any, db: Any, mock: bool = False, llm: LLMClient | None = None
) -> ChatService:
    """Wire LLM client + repo + trading ports. `handle_message` returns the API shape."""
    client = llm or (MockLLMClient() if mock else LiteLLMClient())
    adapter = TradingServiceAdapter(trading)
    return ChatService(client, ChatRepository(db), adapter, build_default_handlers(adapter, adapter))

"""LLM chat integration: client protocol, schema, prompt, actions, chat service."""

from app.llm.adapters import TradingServiceAdapter
from app.llm.client import LiteLLMClient
from app.llm.mock import MockLLMClient
from app.llm.protocols import (
    ChatRepository,
    LLMClient,
    PortfolioPort,
    StoredMessage,
    WatchlistPort,
)
from app.llm.schema import LLMResponse, TradeAction, WatchlistChange
from app.llm.service import ChatResult, ChatService, build_default_handlers

__all__ = [
    "ChatRepository",
    "ChatResult",
    "ChatService",
    "LLMClient",
    "LLMResponse",
    "LiteLLMClient",
    "MockLLMClient",
    "PortfolioPort",
    "StoredMessage",
    "TradeAction",
    "WatchlistChange",
    "TradingServiceAdapter",
    "WatchlistPort",
    "build_default_handlers",
]

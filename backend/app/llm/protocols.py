"""Small role-specific interfaces the chat service depends on (DIP / ISP).

Port methods may be sync or async; the service awaits results when needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Takes chat messages, returns the raw JSON text of the structured response."""

    async def complete(self, messages: list[dict[str, str]]) -> str: ...


@dataclass(frozen=True)
class StoredMessage:
    role: str  # "user" | "assistant"
    content: str


class ChatRepository(Protocol):
    """Persistence for chat_messages (implemented by the db layer)."""

    def add(self, role: str, content: str, actions: dict[str, Any] | list | None = None) -> Any: ...

    def recent(self, limit: int = 20) -> list[Any]:
        """Oldest-first; items expose `.role` and `.content` (or dict keys)."""
        ...


class PortfolioPort(Protocol):
    """Portfolio operations used by chat (implemented by the portfolio service)."""

    def get_context(self) -> dict[str, Any]:
        """Cash, positions with P&L, watchlist with live prices, total value."""
        ...

    def execute_trade(self, ticker: str, side: str, quantity: float) -> Any:
        """Execute a market order; raise an Exception with a readable message on failure.
        If the result is a dict with a "price", it is echoed in the chat response."""
        ...


class WatchlistPort(Protocol):
    def add_ticker(self, ticker: str) -> Any: ...

    def remove_ticker(self, ticker: str) -> Any: ...

"""Action dispatcher (Open/Closed): add a handler to the registry for a new action type."""

from __future__ import annotations

import inspect
from typing import Any, Protocol

from app.llm.protocols import PortfolioPort, WatchlistPort
from app.llm.schema import LLMResponse


async def _resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


class ActionHandler(Protocol):
    async def handle(self, response: LLMResponse) -> list[dict[str, Any]]:
        """Execute this handler's actions; return one result dict per action (never raise)."""
        ...


class TradeHandler:
    def __init__(self, portfolio: PortfolioPort):
        self._portfolio = portfolio

    async def handle(self, response: LLMResponse) -> list[dict[str, Any]]:
        results = []
        for t in response.trades:
            entry: dict[str, Any] = {
                "type": "trade", "ticker": t.ticker, "side": t.side, "quantity": t.quantity,
                "price": None, "error": None,
            }
            try:
                result = await _resolve(self._portfolio.execute_trade(t.ticker, t.side, t.quantity))
                entry["price"] = result.get("price") if isinstance(result, dict) else getattr(result, "price", None)
                entry["status"] = "executed"
            except Exception as exc:  # noqa: BLE001 - reported to user
                entry["status"] = "failed"
                entry["error"] = str(exc) or type(exc).__name__
            results.append(entry)
        return results


class WatchlistHandler:
    def __init__(self, watchlist: WatchlistPort):
        self._watchlist = watchlist

    async def handle(self, response: LLMResponse) -> list[dict[str, Any]]:
        results = []
        for c in response.watchlist_changes:
            entry: dict[str, Any] = {"type": "watchlist", "ticker": c.ticker, "action": c.action, "error": None}
            try:
                fn = self._watchlist.add_ticker if c.action == "add" else self._watchlist.remove_ticker
                await _resolve(fn(c.ticker))
                entry["status"] = "executed"
            except Exception as exc:  # noqa: BLE001
                entry["status"] = "failed"
                entry["error"] = str(exc) or type(exc).__name__
            results.append(entry)
        return results

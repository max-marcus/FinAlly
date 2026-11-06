"""Adapt backend-engineer's TradingService facade to the chat ports (ISP/DIP)."""

from __future__ import annotations

import inspect
from typing import Any


class TradingServiceAdapter:
    """Implements PortfolioPort and WatchlistPort over a TradingService."""

    def __init__(self, trading: Any):
        self._t = trading

    def get_context(self) -> dict[str, Any]:
        return {"portfolio": self._t.get_portfolio(), "watchlist": self._t.get_watchlist()}

    def execute_trade(self, ticker: str, side: str, quantity: float) -> Any:
        return self._t.execute_trade(ticker, side, quantity)

    async def add_ticker(self, ticker: str) -> None:
        if not await _maybe(self._t.add_watchlist(ticker)):
            raise ValueError(f"{ticker} is already on the watchlist or could not be added")

    async def remove_ticker(self, ticker: str) -> None:
        if not await _maybe(self._t.remove_watchlist(ticker)):
            raise ValueError(f"{ticker} is not on the watchlist")


async def _maybe(v: Any) -> Any:
    return await v if inspect.isawaitable(v) else v

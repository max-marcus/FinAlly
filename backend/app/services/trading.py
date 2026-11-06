"""TradingService facade combining portfolio + watchlist for the chat service."""

from __future__ import annotations

from typing import Any

from .errors import NotFoundError
from .portfolio import PortfolioService
from .watchlist import WatchlistService


class TradingFacade:
    def __init__(self, portfolio: PortfolioService, watchlist: WatchlistService) -> None:
        self._portfolio = portfolio
        self._watchlist = watchlist

    def execute_trade(self, ticker: str, side: str, quantity: float) -> dict[str, Any]:
        return self._portfolio.execute_trade(ticker, side, quantity)

    def get_portfolio(self) -> dict[str, Any]:
        return self._portfolio.get_portfolio()

    def get_watchlist(self) -> list[dict[str, Any]]:
        return self._watchlist.list()

    async def add_watchlist(self, ticker: str) -> bool:
        return await self._watchlist.add(ticker)

    async def remove_watchlist(self, ticker: str) -> bool:
        try:
            return await self._watchlist.remove(ticker)
        except NotFoundError:
            return False

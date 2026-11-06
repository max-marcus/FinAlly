"""Watchlist service: persists tickers and keeps the market data source in sync."""

from __future__ import annotations

import re
from typing import Any

from app.market import PriceCache

from .errors import NotFoundError, TradeError
from .portfolio import normalize_ticker
from .protocols import PortfolioRepository, TickerRegistry

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


class WatchlistService:
    def __init__(
        self, repo: PortfolioRepository, source: TickerRegistry, cache: PriceCache
    ) -> None:
        self._repo = repo
        self._source = source
        self._cache = cache

    def list(self) -> list[dict[str, Any]]:
        out = []
        for ticker in self._repo.list_watchlist():
            u = self._cache.get(ticker)
            out.append(
                {
                    "ticker": ticker,
                    "price": u.price if u else None,
                    "previous_price": u.previous_price if u else None,
                    "change": u.change if u else None,
                    "change_percent": u.change_percent if u else None,
                    "direction": u.direction if u else None,
                }
            )
        return out

    async def add(self, ticker: str) -> bool:
        ticker = normalize_ticker(ticker)
        if not TICKER_RE.match(ticker):
            raise TradeError(f"Invalid ticker: {ticker!r}")
        added = self._repo.add_watchlist(ticker)
        await self._source.add_ticker(ticker)
        return added

    async def remove(self, ticker: str) -> bool:
        ticker = normalize_ticker(ticker)
        removed = self._repo.remove_watchlist(ticker)
        if not removed:
            raise NotFoundError(f"{ticker} is not on the watchlist")
        # Keep streaming prices for tickers still held as positions (needed for valuation).
        if not any(p["ticker"] == ticker for p in self._repo.list_positions()):
            await self._source.remove_ticker(ticker)
        return True

"""Small role-specific protocols the services depend on (Dependency Inversion)."""

from __future__ import annotations

from typing import Any, Protocol


class PortfolioRepository(Protocol):
    """Persistence needed by portfolio/watchlist services (single default user).

    `execute_trade_atomic` must apply cash + position + trade-log changes in one
    transaction. Implemented by an adapter over the db package.
    """

    def get_cash(self) -> float: ...
    def list_positions(self) -> list[dict[str, Any]]: ...  # ticker, quantity, avg_cost
    def apply_trade(
        self,
        *,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
        new_cash: float,
        new_quantity: float,
        new_avg_cost: float,
    ) -> dict[str, Any]: ...  # returns trade row dict
    def insert_snapshot(self, total_value: float) -> None: ...
    def list_snapshots(self) -> list[dict[str, Any]]: ...
    def list_watchlist(self) -> list[str]: ...
    def add_watchlist(self, ticker: str) -> bool: ...
    def remove_watchlist(self, ticker: str) -> bool: ...


class PriceLookup(Protocol):
    """Read-only price access (ISP): trade execution only needs this."""

    def get_price(self, ticker: str) -> float | None: ...


class TickerRegistry(Protocol):
    """What the watchlist service needs from a market data source."""

    async def add_ticker(self, ticker: str) -> None: ...
    async def remove_ticker(self, ticker: str) -> None: ...


class TradingService(Protocol):
    """Facade handed to the chat service."""

    def execute_trade(self, ticker: str, side: str, quantity: float) -> dict[str, Any]: ...
    def get_portfolio(self) -> dict[str, Any]: ...
    def get_watchlist(self) -> list[dict[str, Any]]: ...
    async def add_watchlist(self, ticker: str) -> bool: ...
    async def remove_watchlist(self, ticker: str) -> bool: ...


class ChatService(Protocol):
    async def handle_message(self, message: str) -> dict[str, Any]: ...

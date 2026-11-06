"""Adapter: PortfolioRepository protocol over the app.db repositories."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.db import (
    Database,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)

QTY_EPS = 1e-9


class DbPortfolioRepository:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._watch = WatchlistRepository(db)
        self._positions = PositionRepository(db)
        self._trades = TradeRepository(db)
        self._snaps = SnapshotRepository(db)

    def get_cash(self) -> float:
        return self._users.get_cash()

    def list_positions(self) -> list[dict[str, Any]]:
        return [
            {"ticker": p.ticker, "quantity": p.quantity, "avg_cost": p.avg_cost}
            for p in self._positions.list()
        ]

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
    ) -> dict[str, Any]:
        with self._db.transaction():
            self._users.set_cash(new_cash)
            if new_quantity <= QTY_EPS:
                self._positions.delete(ticker)
            else:
                self._positions.upsert(ticker, new_quantity, new_avg_cost)
            trade = self._trades.record(ticker, side, quantity, price)
        d = asdict(trade)
        d.pop("user_id", None)
        return d

    def insert_snapshot(self, total_value: float) -> None:
        self._snaps.record(total_value)

    def list_snapshots(self) -> list[dict[str, Any]]:
        return [
            {"total_value": s.total_value, "recorded_at": s.recorded_at}
            for s in self._snaps.list()
        ]

    def list_watchlist(self) -> list[str]:
        return self._watch.tickers()

    def add_watchlist(self, ticker: str) -> bool:
        return self._watch.add(ticker)

    def remove_watchlist(self, ticker: str) -> bool:
        return self._watch.remove(ticker)

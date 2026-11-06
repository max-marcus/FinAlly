"""Default seed data."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ._util import new_id, now_iso

if TYPE_CHECKING:
    from .connection import Database

DEFAULT_USER_ID = "default"
DEFAULT_CASH = 10000.0
DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


def seed_defaults(db: "Database") -> None:
    """Seed profile + watchlist if no profile exists. Idempotent."""
    if db.query_one("SELECT 1 FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)):
        return
    ts = now_iso()
    db.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH, ts),
    )
    for ticker in DEFAULT_WATCHLIST:
        db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), DEFAULT_USER_ID, ticker, ts),
        )

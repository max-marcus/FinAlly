"""Repositories: thin persistence wrappers, no business logic."""
from __future__ import annotations

import json

from ._util import new_id, now_iso
from .connection import Database
from .models import ChatMessage, Position, Profile, Snapshot, Trade, WatchlistItem

DEFAULT = "default"


def _t(ticker: str) -> str:
    return ticker.strip().upper()


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_profile(self, user_id: str = DEFAULT) -> Profile | None:
        r = self._db.query_one("SELECT * FROM users_profile WHERE id = ?", (user_id,))
        return Profile(r["id"], r["cash_balance"], r["created_at"]) if r else None

    def get_cash(self, user_id: str = DEFAULT) -> float:
        p = self.get_profile(user_id)
        if p is None:
            raise KeyError(f"unknown user {user_id!r}")
        return p.cash_balance

    def set_cash(self, amount: float, user_id: str = DEFAULT) -> None:
        if self._db.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (amount, user_id)
        ) == 0:
            raise KeyError(f"unknown user {user_id!r}")


class WatchlistRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list(self, user_id: str = DEFAULT) -> list[WatchlistItem]:
        rows = self._db.query(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
        )
        return [WatchlistItem(r["id"], r["user_id"], r["ticker"], r["added_at"]) for r in rows]

    def tickers(self, user_id: str = DEFAULT) -> list[str]:
        return [i.ticker for i in self.list(user_id)]

    def add(self, ticker: str, user_id: str = DEFAULT) -> bool:
        return self._db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, _t(ticker), now_iso()),
        ) == 1

    def remove(self, ticker: str, user_id: str = DEFAULT) -> bool:
        return self._db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, _t(ticker))
        ) == 1

    def contains(self, ticker: str, user_id: str = DEFAULT) -> bool:
        return self._db.query_one(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, _t(ticker))
        ) is not None


def _position(r) -> Position:
    return Position(r["id"], r["user_id"], r["ticker"], r["quantity"], r["avg_cost"], r["updated_at"])


class PositionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list(self, user_id: str = DEFAULT) -> list[Position]:
        rows = self._db.query(
            "SELECT * FROM positions WHERE user_id = ? ORDER BY ticker", (user_id,)
        )
        return [_position(r) for r in rows]

    def get(self, ticker: str, user_id: str = DEFAULT) -> Position | None:
        r = self._db.query_one(
            "SELECT * FROM positions WHERE user_id = ? AND ticker = ?", (user_id, _t(ticker))
        )
        return _position(r) if r else None

    def upsert(self, ticker: str, quantity: float, avg_cost: float, user_id: str = DEFAULT) -> Position:
        self._db.execute(
            """INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (user_id, ticker) DO UPDATE SET
                 quantity = excluded.quantity,
                 avg_cost = excluded.avg_cost,
                 updated_at = excluded.updated_at""",
            (new_id(), user_id, _t(ticker), quantity, avg_cost, now_iso()),
        )
        pos = self.get(ticker, user_id)
        assert pos is not None
        return pos

    def delete(self, ticker: str, user_id: str = DEFAULT) -> bool:
        return self._db.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, _t(ticker))
        ) == 1


class TradeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record(self, ticker: str, side: str, quantity: float, price: float, user_id: str = DEFAULT) -> Trade:
        if side not in ("buy", "sell"):
            raise ValueError(f"invalid side {side!r}")
        t = Trade(new_id(), user_id, _t(ticker), side, quantity, price, now_iso())
        self._db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?,?,?,?,?,?,?)",
            (t.id, t.user_id, t.ticker, t.side, t.quantity, t.price, t.executed_at),
        )
        return t

    def list(self, user_id: str = DEFAULT, limit: int | None = None) -> list[Trade]:
        sql = "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC"
        params: list = [user_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return [
            Trade(r["id"], r["user_id"], r["ticker"], r["side"], r["quantity"], r["price"], r["executed_at"])
            for r in self._db.query(sql, params)
        ]


class SnapshotRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record(self, total_value: float, user_id: str = DEFAULT) -> Snapshot:
        s = Snapshot(new_id(), user_id, total_value, now_iso())
        self._db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?,?,?,?)",
            (s.id, s.user_id, s.total_value, s.recorded_at),
        )
        return s

    def list(self, user_id: str = DEFAULT, limit: int | None = None) -> list[Snapshot]:
        if limit is None:
            rows = self._db.query(
                "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at, rowid",
                (user_id,),
            )
        else:
            rows = self._db.query(
                """SELECT * FROM (SELECT *, rowid AS rid FROM portfolio_snapshots WHERE user_id = ?
                   ORDER BY recorded_at DESC, rowid DESC LIMIT ?) ORDER BY recorded_at, rid""",
                (user_id, limit),
            )
        return [Snapshot(r["id"], r["user_id"], r["total_value"], r["recorded_at"]) for r in rows]

    def prune(self, keep: int, user_id: str = DEFAULT) -> int:
        return self._db.execute(
            """DELETE FROM portfolio_snapshots WHERE user_id = ? AND rowid NOT IN (
                 SELECT rowid FROM portfolio_snapshots WHERE user_id = ?
                 ORDER BY recorded_at DESC, rowid DESC LIMIT ?)""",
            (user_id, user_id, keep),
        )


class ChatRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, role: str, content: str, actions=None, user_id: str = DEFAULT) -> ChatMessage:
        if role not in ("user", "assistant"):
            raise ValueError(f"invalid role {role!r}")
        m = ChatMessage(new_id(), user_id, role, content, actions, now_iso())
        self._db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?,?,?,?,?,?)",
            (m.id, m.user_id, m.role, m.content,
             json.dumps(actions) if actions is not None else None, m.created_at),
        )
        return m

    def recent(self, limit: int = 20, user_id: str = DEFAULT) -> list[ChatMessage]:
        rows = self._db.query(
            """SELECT * FROM (SELECT *, rowid AS rid FROM chat_messages WHERE user_id = ?
               ORDER BY created_at DESC, rowid DESC LIMIT ?) ORDER BY created_at, rid""",
            (user_id, limit),
        )
        return [
            ChatMessage(r["id"], r["user_id"], r["role"], r["content"],
                        json.loads(r["actions"]) if r["actions"] else None, r["created_at"])
            for r in rows
        ]

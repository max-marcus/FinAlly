"""Plain record types returned by repositories."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Profile:
    id: str
    cash_balance: float
    created_at: str


@dataclass(frozen=True)
class WatchlistItem:
    id: str
    user_id: str
    ticker: str
    added_at: str


@dataclass(frozen=True)
class Position:
    id: str
    user_id: str
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str


@dataclass(frozen=True)
class Trade:
    id: str
    user_id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


@dataclass(frozen=True)
class Snapshot:
    id: str
    user_id: str
    total_value: float
    recorded_at: str


@dataclass(frozen=True)
class ChatMessage:
    id: str
    user_id: str
    role: str
    content: str
    actions: Any
    created_at: str

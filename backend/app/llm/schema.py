"""Structured-output schema the LLM must produce."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("side", mode="before")
    @classmethod
    def _lower_side(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("action", mode="before")
    @classmethod
    def _lower_action(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)

    @field_validator("trades", "watchlist_changes", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return [] if v is None else v

"""Deterministic mock LLM for LLM_MOCK=true. Triggers documented in planning/LLM_MOCK.md."""

from __future__ import annotations

import json
import re

_ADD = re.compile(r"\badd\s+\$?([A-Za-z]{1,5})\b", re.I)
_REMOVE = re.compile(r"\bremove\s+\$?([A-Za-z]{1,5})\b", re.I)
_BUY = re.compile(r"\bbuy\b(?:\s+(\d+(?:\.\d+)?))?(?:\s+(?:shares?\s+of\s+)?\$?([A-Za-z]{1,5})\b)?", re.I)
_SELL = re.compile(r"\bsell\b(?:\s+(\d+(?:\.\d+)?))?(?:\s+(?:shares?\s+of\s+)?\$?([A-Za-z]{1,5})\b)?", re.I)
_STOP = {"a", "an", "the", "some", "shares", "share", "of", "me", "it", "to", "my", "stock"}


def _trade_args(match: re.Match) -> tuple[str, float]:
    qty, ticker = match.group(1), match.group(2)
    if ticker and (ticker.lower() in _STOP):
        ticker = None
    return (ticker or "AAPL").upper(), float(qty) if qty else 1.0


class MockLLMClient:
    """Pure function of the last user message; ignores portfolio context."""

    async def complete(self, messages: list[dict[str, str]]) -> str:
        user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return json.dumps(self.respond(user_text))

    @staticmethod
    def respond(text: str) -> dict:
        trades: list[dict] = []
        changes: list[dict] = []
        if m := _BUY.search(text):
            ticker, qty = _trade_args(m)
            trades.append({"ticker": ticker, "side": "buy", "quantity": qty})
            message = f"Buying {qty:g} {ticker} at market."
        elif m := _SELL.search(text):
            ticker, qty = _trade_args(m)
            trades.append({"ticker": ticker, "side": "sell", "quantity": qty})
            message = f"Selling {qty:g} {ticker} at market."
        elif m := _ADD.search(text):
            ticker = m.group(1).upper()
            changes.append({"ticker": ticker, "action": "add"})
            message = f"Adding {ticker} to your watchlist."
        elif m := _REMOVE.search(text):
            ticker = m.group(1).upper()
            changes.append({"ticker": ticker, "action": "remove"})
            message = f"Removing {ticker} from your watchlist."
        else:
            message = (
                "Mock analysis: your portfolio looks reasonably diversified. "
                "Consider watching concentration risk in your largest positions."
            )
        return {"message": message, "trades": trades, "watchlist_changes": changes}

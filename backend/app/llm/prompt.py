"""Prompt construction: system message + portfolio context + history + new user message."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation \
(fake money, market orders only, instant fills, no fees).

Your job:
- Analyze portfolio composition, risk concentration and P&L.
- Suggest trades with brief reasoning.
- Execute trades when the user asks or agrees, by listing them in "trades".
- Manage the watchlist proactively via "watchlist_changes" (action "add" or "remove").
- Be concise and data-driven.

Always respond with valid JSON matching this schema and nothing else:
{"message": string, "trades": [{"ticker": string, "side": "buy"|"sell", "quantity": number}], \
"watchlist_changes": [{"ticker": string, "action": "add"|"remove"}]}
Use empty arrays when there is nothing to execute. Only include trades the user requested or agreed to. \
Trades are validated (cash, shares owned); failures are reported back to the user."""


def build_messages(
    context: dict[str, Any],
    history: list[tuple[str, str]],
    user_message: str,
) -> list[dict[str, str]]:
    system = f"{SYSTEM_PROMPT}\n\nCurrent portfolio context (JSON):\n{json.dumps(context, default=str)}"
    messages = [{"role": "system", "content": system}]
    messages += [{"role": role, "content": content} for role, content in history]
    messages.append({"role": "user", "content": user_message})
    return messages

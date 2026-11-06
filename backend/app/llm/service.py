"""Chat service: prompt -> LLM -> parse -> auto-execute actions -> persist -> result."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.llm.actions import ActionHandler, TradeHandler, WatchlistHandler
from app.llm.prompt import build_messages
from app.llm.protocols import ChatRepository, LLMClient, PortfolioPort, WatchlistPort
from app.llm.schema import LLMResponse

HISTORY_LIMIT = 20
FALLBACK_MESSAGE = "Sorry, I had trouble producing a valid response. Please try again."


async def _resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def build_default_handlers(portfolio: PortfolioPort, watchlist: WatchlistPort) -> list[ActionHandler]:
    return [TradeHandler(portfolio), WatchlistHandler(watchlist)]


def parse_llm_output(raw: str) -> LLMResponse:
    """Parse raw model text; tolerate code fences / surrounding prose. Raises ValueError."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return LLMResponse.model_validate_json(text)
    except ValidationError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return LLMResponse.model_validate_json(text[start : end + 1])
            except ValidationError as exc:
                raise ValueError(str(exc)) from exc
        raise ValueError("response was not valid JSON matching the schema") from None


@dataclass
class ChatResult:
    message: str
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """POST /api/chat response shape (planning/API_CONTRACT.md)."""
        def pick(a, keys):
            return {k: a.get(k) for k in keys}
        return {
            "message": self.message,
            "trades": [
                pick(a, ("ticker", "side", "quantity", "price", "status", "error"))
                for a in self.actions if a["type"] == "trade"
            ],
            "watchlist_changes": [
                pick(a, ("ticker", "action", "status", "error"))
                for a in self.actions if a["type"] == "watchlist"
            ],
        }


class ChatService:
    def __init__(
        self,
        llm: LLMClient,
        repo: ChatRepository,
        portfolio: PortfolioPort,
        handlers: list[ActionHandler],
        history_limit: int = HISTORY_LIMIT,
    ):
        self._llm = llm
        self._repo = repo
        self._portfolio = portfolio
        self._handlers = handlers
        self._history_limit = history_limit

    async def handle_message(self, message: str) -> dict[str, Any]:
        """Implements the app.services.protocols.ChatService contract."""
        return (await self.chat(message)).to_dict()

    async def chat(self, user_message: str) -> ChatResult:
        context = await _resolve(self._portfolio.get_context())
        stored = await _resolve(self._repo.recent(self._history_limit))
        history = [_role_content(m) for m in stored]
        messages = build_messages(context, history, user_message)

        await _resolve(self._repo.add("user", user_message, None))

        try:
            raw = await self._llm.complete(messages)
            parsed = parse_llm_output(raw)
        except Exception:  # noqa: BLE001 - LLM/network/parse failure must not 500 the chat
            parsed = LLMResponse(message=FALLBACK_MESSAGE)

        actions: list[dict[str, Any]] = []
        for handler in self._handlers:
            actions.extend(await handler.handle(parsed))

        message = parsed.message
        failures = [a for a in actions if a["status"] == "failed"]
        if failures:
            lines = [
                f"- {_describe(a)} failed: {a['error']}" for a in failures
            ]
            message = f"{message}\n\nSome actions could not be completed:\n" + "\n".join(lines)

        await _resolve(self._repo.add("assistant", message, {"actions": actions}))
        return ChatResult(message=message, actions=actions)


def _describe(a: dict[str, Any]) -> str:
    if a["type"] == "trade":
        return f"{a['side']} {a['quantity']:g} {a['ticker']}"
    return f"{a['action']} {a['ticker']} (watchlist)"


def _role_content(m: Any) -> tuple[str, str]:
    if isinstance(m, dict):
        return m["role"], m["content"]
    return m.role, m.content

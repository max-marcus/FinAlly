"""Real LLM client: LiteLLM -> OpenRouter -> Cerebras (gpt-oss-120b), structured output."""

from __future__ import annotations

import asyncio

from app.llm.schema import LLMResponse

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


class LiteLLMClient:
    def __init__(self, model: str = MODEL, reasoning_effort: str = "low", timeout: float = 60.0):
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    async def complete(self, messages: list[dict[str, str]]) -> str:
        # Imported lazily so tests / mock mode never pay for (or need) litellm.
        from litellm import completion

        def _call() -> str:
            response = completion(
                model=self._model,
                messages=messages,
                response_format=LLMResponse,
                reasoning_effort=self._reasoning_effort,
                extra_body=EXTRA_BODY,
                timeout=self._timeout,
            )
            return response.choices[0].message.content or ""

        return await asyncio.to_thread(_call)

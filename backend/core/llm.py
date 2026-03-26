from __future__ import annotations

import asyncio
import json
import random
from typing import TypeVar

from anthropic import AsyncAnthropic, RateLimitError
from pydantic import BaseModel

from config import settings


T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    pass


_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if not settings.anthropic_api_key:
        raise LLMUnavailableError("ANTHROPIC_API_KEY is not configured.")
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def complete(system: str, user: str) -> str:
    client = get_client()
    delay = 0.5
    for attempt in range(3):
        try:
            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text_blocks = [block.text for block in response.content if getattr(block, "type", "") == "text"]
            return "\n".join(text_blocks).strip()
        except RateLimitError:
            if attempt == 2:
                raise
            await asyncio.sleep(delay + random.uniform(0.0, 0.25))
            delay *= 2
    raise RuntimeError("Anthropic completion failed after retries.")


async def complete_json(system: str, user: str, response_model: type[T]) -> T:
    for attempt in range(3):
        raw = await complete(system, user)
        try:
            parsed = json.loads(raw)
            return response_model.model_validate(parsed)
        except Exception:
            if attempt == 2:
                raise
    raise RuntimeError("Anthropic JSON completion failed after retries.")

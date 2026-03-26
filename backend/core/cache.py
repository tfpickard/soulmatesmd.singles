from __future__ import annotations

import json
from typing import Any, Protocol

from upstash_redis.asyncio import Redis as UpstashRedis

from config import settings


class CacheBackend(Protocol):
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...


class UpstashCache:
    def __init__(self) -> None:
        assert settings.upstash_redis_rest_url is not None
        assert settings.upstash_redis_rest_token is not None
        self.client = UpstashRedis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )

    async def get_json(self, key: str) -> dict[str, Any] | None:
        value = await self.client.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, bytes):
            return json.loads(value.decode("utf-8"))
        return value

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        await self.client.set(key, json.dumps(value), ex=ttl_seconds)


_cache: CacheBackend | None = None


def get_cache() -> CacheBackend | None:
    global _cache
    if _cache is not None:
        return _cache
    if settings.upstash_redis_rest_url and settings.upstash_redis_rest_token:
        _cache = UpstashCache()
        return _cache
    return None

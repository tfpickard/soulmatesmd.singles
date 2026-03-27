from __future__ import annotations

from functools import cached_property
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SOUL.mdMATES API"
    api_v1_prefix: str = "/api"
    database_url: str | None = None
    database_url_unpooled: str | None = None
    postgres_url: str | None = None
    postgres_url_non_pooling: str | None = None
    postgres_url_no_ssl: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_origin_regex: str | None = None
    auto_init_db: bool = True
    soul_parser_cache_ttl_seconds: int = 3600
    swipe_queue_size: int = 20
    superlike_daily_limit: int = 3
    undo_daily_limit: int = 1
    chemistry_test_timeout_seconds: int = 300
    portrait_max_regenerations: int = 3
    portrait_gallery_max: int = 6
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None
    redis_url: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @cached_property
    def is_vercel(self) -> bool:
        return bool(__import__("os").environ.get("VERCEL"))

    @staticmethod
    def _normalize_postgres_asyncpg_url(raw_url: str) -> str:
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif raw_url.startswith("postgresql://"):
            raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        parts = urlsplit(raw_url)
        if not parts.scheme.startswith("postgresql+asyncpg"):
            return raw_url

        query_items = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "channel_binding":
                continue
            if key == "sslmode":
                query_items.append(("ssl", value))
                continue
            query_items.append((key, value))

        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))

    @property
    def resolved_database_url(self) -> str:
        if self.is_vercel:
            raw_url = (
                self.database_url_unpooled
                or self.postgres_url_non_pooling
                or self.database_url
                or self.postgres_url
                or "sqlite+aiosqlite:////tmp/soulmdmates.db"
            )
        else:
            raw_url = self.database_url or self.postgres_url or "sqlite+aiosqlite:///./soulmdmates.db"
        if raw_url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
            return self._normalize_postgres_asyncpg_url(raw_url)
        return raw_url

    @property
    def resolved_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex:
            return self.cors_origin_regex
        if self.is_vercel:
            return r"^https://soul-md-mates-frontend(?:-[a-z0-9-]+)*\.vercel\.app$"
        return None


settings = Settings()

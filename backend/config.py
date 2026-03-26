from __future__ import annotations

from functools import cached_property
from typing import Any

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
    postgres_url: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    auto_init_db: bool = True
    soul_parser_cache_ttl_seconds: int = 3600
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

    @property
    def resolved_database_url(self) -> str:
        raw_url = self.database_url or self.postgres_url or "sqlite+aiosqlite:///./soulmdmates.db"
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return raw_url


settings = Settings()

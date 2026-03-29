from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env.local"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "soulmatesmd.singles API"
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
    admin_email: str | None = None
    admin_password: str | None = None
    admin_session_ttl_hours: int = 24
    admin_session_secret: str | None = None
    password_reset_ttl_hours: int = 2
    password_reset_secret: str | None = None
    frontend_base_url: str = "http://localhost:5173"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = True
    hf_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HF_API_TOKEN"),
    )
    hf_image_model: str = "ByteDance/SDXL-Lightning"
    blob_read_write_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BLOB_READ_WRITE_TOKEN", "VERCEL_BLOB_READ_WRITE_TOKEN", "BLOB_TOKEN"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @cached_property
    def is_vercel(self) -> bool:
        return bool(__import__("os").environ.get("VERCEL"))

    @cached_property
    def is_railway(self) -> bool:
        return bool(__import__("os").environ.get("RAILWAY_ENVIRONMENT"))

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
            # Vercel serverless: prefer unpooled to avoid connection limits
            raw_url = (
                self.database_url_unpooled
                or self.postgres_url_non_pooling
                or self.database_url
                or self.postgres_url
            )
            if not raw_url:
                raise RuntimeError("VERCEL is set but no durable Postgres URL is configured.")
        elif self.is_railway:
            # Railway: persistent process, pooled connection is fine and preferred
            raw_url = (
                self.database_url
                or self.postgres_url
                or self.database_url_unpooled
                or self.postgres_url_non_pooling
            )
            if not raw_url:
                raise RuntimeError("RAILWAY_ENVIRONMENT is set but no Postgres URL is configured.")
        else:
            raw_url = self.database_url or self.postgres_url or "sqlite+aiosqlite:///./soulmdmates.db"
        if raw_url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
            return self._normalize_postgres_asyncpg_url(raw_url)
        return raw_url

    @property
    def database_mode(self) -> str:
        url = self.resolved_database_url
        if url.startswith("sqlite+"):
            return "sqlite"
        if url.startswith("postgresql+asyncpg://"):
            return "postgres"
        return "unknown"

    @property
    def is_durable_database(self) -> bool:
        return self.database_mode == "postgres"

    @property
    def has_redis_cache(self) -> bool:
        return bool((self.upstash_redis_rest_url and self.upstash_redis_rest_token) or self.redis_url)

    @property
    def has_blob_storage(self) -> bool:
        return bool(self.blob_read_write_token)

    @property
    def has_portrait_provider(self) -> bool:
        return bool(self.hf_token)

    @property
    def effective_password_reset_secret(self) -> str:
        return self.password_reset_secret or self.admin_session_secret or "password-reset-secret"

    @property
    def has_smtp_email(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def resolved_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex:
            return self.cors_origin_regex
        patterns = [r"soulmatesmd\.singles", r"www\.soulmatesmd\.singles"]
        if self.is_vercel:
            patterns.append(r"soul-md-mates-frontend(?:-[a-z0-9-]+)*\.vercel\.app")
        if self.is_railway:
            patterns.append(r".*\.up\.railway\.app")
        if patterns:
            return r"^https://(?:" + "|".join(patterns) + r")$"
        return None


settings = Settings()

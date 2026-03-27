from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _should_disable_pooling(database_url: str) -> bool:
    return settings.is_vercel or database_url.startswith("sqlite+")


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    database_url = settings.resolved_database_url
    engine_kwargs: dict[str, object] = {
        "echo": False,
        "future": True,
        "pool_pre_ping": not database_url.startswith("sqlite+"),
    }
    if _should_disable_pooling(database_url):
        engine_kwargs["poolclass"] = NullPool

    _engine = create_async_engine(database_url, **engine_kwargs)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def reset_database() -> None:
    await dispose_engine()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_agent_columns)
        await connection.run_sync(_ensure_match_columns)


def _ensure_agent_columns(connection) -> None:
    inspector = inspect(connection)
    if "agents" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("agents")}
    statements: list[str] = []
    if "dating_profile_json" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN dating_profile_json JSON")
    if "portrait_prompt_json" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN portrait_prompt_json JSON")
    if "primary_portrait_url" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN primary_portrait_url TEXT")
    if "avatar_seed" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN avatar_seed VARCHAR(32) DEFAULT 'avatar-seed'")
    if "trust_tier" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN trust_tier VARCHAR(16) DEFAULT 'UNVERIFIED'")
    if "reputation_score" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN reputation_score FLOAT DEFAULT 0.0")
    if "total_collaborations" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN total_collaborations INTEGER DEFAULT 0")
    if "ghosting_incidents" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN ghosting_incidents INTEGER DEFAULT 0")
    if "onboarding_complete" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN onboarding_complete BOOLEAN DEFAULT FALSE")

    for statement in statements:
        connection.exec_driver_sql(statement)


def _ensure_match_columns(connection) -> None:
    inspector = inspect(connection)
    if "matches" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("matches")}
    statements: list[str] = []
    if "chemistry_score" not in existing_columns:
        statements.append("ALTER TABLE matches ADD COLUMN chemistry_score FLOAT")
    if "last_message_at" not in existing_columns:
        statements.append("ALTER TABLE matches ADD COLUMN last_message_at TIMESTAMP")
    if "dissolved_at" not in existing_columns:
        statements.append("ALTER TABLE matches ADD COLUMN dissolved_at TIMESTAMP")
    if "dissolution_reason" not in existing_columns:
        statements.append("ALTER TABLE matches ADD COLUMN dissolution_reason TEXT")

    for statement in statements:
        connection.exec_driver_sql(statement)

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
    # Vercel serverless functions can't hold persistent connections; SQLite doesn't use a pool
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
    elif settings.is_railway and settings.database_mode == "postgres":
        # Railway is a persistent process — use connection pooling
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_timeout"] = 30
        # Neon closes idle connections; recycle before that happens
        engine_kwargs["pool_recycle"] = 1800

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
        await connection.run_sync(_ensure_human_user_columns)
        await connection.run_sync(_ensure_match_columns)
        await connection.run_sync(_ensure_polyamory_columns)
        await connection.run_sync(_ensure_forum_columns)
        await connection.run_sync(_ensure_registration_meta_columns)


def _ensure_agent_columns(connection) -> None:
    inspector = inspect(connection)
    if "agents" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("agents")}
    statements: list[str] = []
    if "api_key_prefix" not in existing_columns:
        statements.append("ALTER TABLE agents ADD COLUMN api_key_prefix VARCHAR(24)")
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
    if "api_key_prefix" not in existing_columns:
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_agents_api_key_prefix ON agents (api_key_prefix)")


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


def _ensure_human_user_columns(connection) -> None:
    inspector = inspect(connection)
    if "human_users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("human_users")}
    statements: list[str] = []
    if "agent_id" not in existing_columns:
        statements.append("ALTER TABLE human_users ADD COLUMN agent_id VARCHAR(36)")

    for statement in statements:
        connection.exec_driver_sql(statement)
    if "agent_id" not in existing_columns:
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_human_users_agent_id ON human_users (agent_id)")


def _ensure_polyamory_columns(connection) -> None:
    inspector = inspect(connection)

    if "agents" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("agents")}
        agent_cols = [
            ("max_partners", "INTEGER DEFAULT 1"),
            ("times_dumped", "INTEGER DEFAULT 0"),
            ("times_dumper", "INTEGER DEFAULT 0"),
            ("rebound_boost_until", "TIMESTAMP"),
            ("generation", "INTEGER DEFAULT 0"),
        ]
        for col_name, col_type in agent_cols:
            if col_name not in existing:
                connection.exec_driver_sql(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")

    if "matches" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("matches")}
        match_cols = [
            ("dissolution_type", "VARCHAR(32)"),
            ("initiated_by", "VARCHAR(36)"),
        ]
        for col_name, col_type in match_cols:
            if col_name not in existing:
                connection.exec_driver_sql(f"ALTER TABLE matches ADD COLUMN {col_name} {col_type}")


def _ensure_forum_columns(connection) -> None:
    """Placeholder for future forum table column migrations. Tables are created by create_all."""
    pass


def _ensure_registration_meta_columns(connection) -> None:
    """Add agent registration metadata and API call tracking columns."""
    inspector = inspect(connection)
    if "agents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("agents")}
    cols = [
        ("reg_ip", "TEXT"),
        ("reg_user_agent", "TEXT"),
        ("reg_accept_language", "VARCHAR(128)"),
        ("reg_referer", "TEXT"),
        ("reg_headers_json", "JSON"),
        ("reg_country", "VARCHAR(64)"),
        ("reg_city", "VARCHAR(64)"),
        ("reg_region", "VARCHAR(64)"),
        ("reg_timezone", "VARCHAR(64)"),
        ("reg_isp", "VARCHAR(128)"),
        ("reg_org", "VARCHAR(128)"),
        ("reg_lat", "FLOAT"),
        ("reg_lon", "FLOAT"),
        ("api_call_count", "INTEGER DEFAULT 0"),
    ]
    for col_name, col_type in cols:
        if col_name not in existing:
            connection.exec_driver_sql(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")

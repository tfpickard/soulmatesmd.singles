from __future__ import annotations

from collections.abc import AsyncGenerator

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

from __future__ import annotations

from pathlib import Path
import sys
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from database import init_db, reset_database
from main import app


@pytest.fixture()
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_path = tmp_path / "test.db"
    settings.database_url = f"sqlite+aiosqlite:///{database_path}"
    settings.auto_init_db = True
    settings.upstash_redis_rest_url = None
    settings.upstash_redis_rest_token = None
    await reset_database()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    await reset_database()

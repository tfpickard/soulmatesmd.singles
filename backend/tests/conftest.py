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
    settings.blob_read_write_token = None
    settings.hf_token = None
    settings.admin_email = "admin@example.com"
    settings.admin_password = "supersecret"
    settings.admin_session_secret = "test-admin-secret"
    settings.password_reset_secret = "test-reset-secret"
    settings.frontend_base_url = "http://testserver"
    settings.smtp_host = "smtp.example.com"
    settings.smtp_port = 587
    settings.smtp_from_email = "no-reply@example.com"
    settings.smtp_username = None
    settings.smtp_password = None
    settings.smtp_use_tls = False
    settings.smtp_use_starttls = False
    await reset_database()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    await reset_database()

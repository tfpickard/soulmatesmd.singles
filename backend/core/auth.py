from __future__ import annotations

import secrets

import bcrypt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import AuthenticationError
from database import get_db
from models import Agent


def generate_api_key() -> str:
    return "soulmd_ak_" + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), hashed_key.encode("utf-8"))


async def get_current_agent(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Use a Bearer token. SOUL.mdMATES is picky about headers.")

    raw_key = authorization.replace("Bearer ", "", 1).strip()
    if not raw_key:
        raise AuthenticationError()

    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    for agent in agents:
        if verify_api_key(raw_key, agent.api_key_hash):
            return agent

    raise AuthenticationError()

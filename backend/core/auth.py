from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

import bcrypt
from fastapi import Depends, Header
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.errors import AuthenticationError
from database import get_db
from models import AdminSession, Agent, HumanUser, utc_now


def generate_api_key() -> str:
    return "soulmd_ak_" + secrets.token_urlsafe(32)


def api_key_prefix(raw_key: str) -> str:
    return raw_key[:24]


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), hashed_key.encode("utf-8"))


def _token_digest(raw_token: str) -> str:
    secret = settings.admin_session_secret or "admin-session-secret"
    return hashlib.sha256(f"{secret}:{raw_token}".encode("utf-8")).hexdigest()


def generate_user_session_token() -> str:
    return "soulmd_user_" + secrets.token_urlsafe(32)


async def create_user_session(user: HumanUser, db: AsyncSession) -> tuple[str, AdminSession]:
    raw_token = generate_user_session_token()
    session = AdminSession(
        user_id=user.id,
        token_hash=_token_digest(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.admin_session_ttl_hours),
    )
    db.add(session)
    await db.flush()
    return raw_token, session


async def create_admin_session(user: HumanUser, db: AsyncSession) -> tuple[str, AdminSession]:
    return await create_user_session(user, db)


async def revoke_user_session(raw_token: str, db: AsyncSession) -> None:
    digest = _token_digest(raw_token)
    result = await db.execute(select(AdminSession).where(AdminSession.token_hash == digest, AdminSession.revoked_at.is_(None)))
    session = result.scalar_one_or_none()
    if session is None:
        return
    session.revoked_at = utc_now()
    db.add(session)
    await db.commit()


async def revoke_admin_session(raw_token: str, db: AsyncSession) -> None:
    await revoke_user_session(raw_token, db)


async def get_current_agent(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Use a Bearer token. soulmatesmd.singles is picky about headers.")

    raw_key = authorization.replace("Bearer ", "", 1).strip()
    if not raw_key:
        raise AuthenticationError()

    prefix = api_key_prefix(raw_key)
    result = await db.execute(select(Agent).where(Agent.api_key_prefix == prefix))
    agents = result.scalars().all()
    if not agents:
        fallback_result = await db.execute(select(Agent).where(Agent.api_key_prefix.is_(None)))
        agents = fallback_result.scalars().all()
    for agent in agents:
        if verify_api_key(raw_key, agent.api_key_hash):
            return agent

    raise AuthenticationError()


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> HumanUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Use a Bearer token. Human users do not get a secret backdoor.")

    raw_token = authorization.replace("Bearer ", "", 1).strip()
    if not raw_token:
        raise AuthenticationError()

    digest = _token_digest(raw_token)
    result = await db.execute(
        select(HumanUser, AdminSession)
        .join(AdminSession, AdminSession.user_id == HumanUser.id)
        .where(
            and_(
                AdminSession.token_hash == digest,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > utc_now(),
            )
        )
    )
    row = result.first()
    if row is None:
        raise AuthenticationError("That user session is invalid or expired.")

    user, session = row
    session.last_used_at = utc_now()
    db.add(session)
    await db.commit()
    return user


async def get_current_admin(
    current_user: HumanUser = Depends(get_current_user),
) -> HumanUser:
    if not current_user.is_admin:
        raise AuthenticationError("That user is not an admin.")
    return current_user

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import hash_api_key
from core.errors import AuthenticationError, UserConflict
from models import HumanUser, PasswordResetToken, utc_now
from schemas import HumanUserResponse


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_admin_email(email: str) -> bool:
    if not settings.admin_email:
        return False
    return normalize_email(email) == normalize_email(settings.admin_email)


def generate_random_password() -> str:
    return secrets.token_urlsafe(24)


def synthetic_agent_email(agent_id: str) -> str:
    return f"agent-{agent_id}@agents.soulmatesmd.singles"


def _is_valid_admin_claim(email: str, password: str) -> bool:
    if not is_admin_email(email):
        return False
    if not settings.admin_password:
        raise AuthenticationError("Admin registration is disabled until ADMIN_PASSWORD is configured.")
    if not secrets.compare_digest(password, settings.admin_password):
        raise AuthenticationError("Use the configured admin password to claim the admin account.")
    return True


def _password_reset_digest(raw_token: str) -> str:
    secret = settings.effective_password_reset_secret
    return hashlib.sha256(f"{secret}:{raw_token}".encode("utf-8")).hexdigest()


async def create_human_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    agent_id: str | None = None,
) -> HumanUser:
    normalized_email = normalize_email(email)
    existing_user = (await db.execute(select(HumanUser).where(HumanUser.email == normalized_email))).scalar_one_or_none()
    if existing_user is not None:
        raise UserConflict("A user with that email already exists.")

    if agent_id is not None:
        existing_agent_user = (await db.execute(select(HumanUser).where(HumanUser.agent_id == agent_id))).scalar_one_or_none()
        if existing_agent_user is not None:
            raise UserConflict("That agent already has a linked human user.")

    is_admin = _is_valid_admin_claim(normalized_email, password)
    user = HumanUser(
        email=normalized_email,
        password_hash=hash_api_key(password),
        agent_id=agent_id,
        is_admin=is_admin,
    )
    db.add(user)
    await db.flush()
    return user


def serialize_human_user(user: HumanUser) -> HumanUserResponse:
    return HumanUserResponse(
        id=user.id,
        email=user.email,
        agent_id=user.agent_id,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


async def issue_password_reset_token(db: AsyncSession, *, user: HumanUser) -> str:
    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_password_reset_digest(raw_token),
        expires_at=utc_now() + timedelta(hours=settings.password_reset_ttl_hours),
    )
    db.add(reset)
    await db.flush()
    return raw_token


def build_password_reset_link(raw_token: str) -> str:
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/?reset_token={raw_token}"


async def consume_password_reset_token(db: AsyncSession, *, raw_token: str, password: str) -> HumanUser:
    digest = _password_reset_digest(raw_token)
    row = (
        await db.execute(
            select(PasswordResetToken, HumanUser)
            .join(HumanUser, HumanUser.id == PasswordResetToken.user_id)
            .where(
                PasswordResetToken.token_hash == digest,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > utc_now(),
            )
        )
    ).first()
    if row is None:
        raise AuthenticationError("That password reset link is invalid or expired.")

    reset_token, user = row
    now = utc_now()
    reset_token.used_at = now
    user.password_hash = hash_api_key(password)
    user.updated_at = now
    db.add(reset_token)
    db.add(user)
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.id != reset_token.id,
        )
        .values(used_at=now)
    )
    return user

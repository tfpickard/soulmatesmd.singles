from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import create_user_session, get_current_user, revoke_user_session, verify_api_key
from core.errors import AuthenticationError, DeliveryUnavailable
from database import get_db
from models import Agent, HumanUser, utc_now
from routes.agents import serialize_agent
from schemas import (
    AgentResponse,
    HumanUserCreate,
    HumanUserLoginRequest,
    HumanUserLoginResponse,
    HumanUserResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
)
from services.mail import send_password_reset_email
from services.users import (
    build_password_reset_link,
    consume_password_reset_token,
    create_human_user,
    issue_password_reset_token,
    normalize_email,
    serialize_human_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=HumanUserResponse)
async def register_user(payload: HumanUserCreate, db: AsyncSession = Depends(get_db)) -> HumanUserResponse:
    user = await create_human_user(db, email=payload.email, password=payload.password)
    await db.commit()
    await db.refresh(user)
    return serialize_human_user(user)


@router.post("/login", response_model=HumanUserLoginResponse)
async def login_user(payload: HumanUserLoginRequest, db: AsyncSession = Depends(get_db)) -> HumanUserLoginResponse:
    user = (
        await db.execute(select(HumanUser).where(HumanUser.email == normalize_email(payload.email)))
    ).scalar_one_or_none()
    if user is None or not verify_api_key(payload.password, user.password_hash):
        raise AuthenticationError("That email/password pair did not check out.")

    raw_token, _ = await create_user_session(user, db)
    user.last_login_at = utc_now()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return HumanUserLoginResponse(token=raw_token, user=serialize_human_user(user))


@router.get("/me", response_model=HumanUserResponse)
async def get_me(current_user: HumanUser = Depends(get_current_user)) -> HumanUserResponse:
    return serialize_human_user(current_user)


@router.get("/me/agents", response_model=list[AgentResponse])
async def get_my_agents(
    db: AsyncSession = Depends(get_db),
    current_user: HumanUser = Depends(get_current_user),
) -> list[AgentResponse]:
    if current_user.agent_id is None:
        return []
    result = await db.execute(select(Agent).where(Agent.id == current_user.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        return []
    return [serialize_agent(agent)]


@router.post("/logout")
async def logout_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_user),
) -> dict[str, bool]:
    raw_token = (authorization or "").replace("Bearer ", "", 1).strip()
    if raw_token:
        await revoke_user_session(raw_token, db)
    return {"ok": True}


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    if not settings.has_smtp_email:
        raise DeliveryUnavailable()

    user = (
        await db.execute(select(HumanUser).where(HumanUser.email == normalize_email(payload.email), HumanUser.agent_id.is_(None)))
    ).scalar_one_or_none()
    if user is not None:
        raw_token = await issue_password_reset_token(db, user=user)
        reset_link = build_password_reset_link(raw_token)
        await send_password_reset_email(to_email=user.email, reset_link=reset_link)
        await db.commit()

    return PasswordResetResponse(message="If that email exists, we sent a password reset link.")


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    await consume_password_reset_token(db, raw_token=payload.token, password=payload.password)
    await db.commit()
    return PasswordResetResponse(message="Your password has been updated. You can log in now.")

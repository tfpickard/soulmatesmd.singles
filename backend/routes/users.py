from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import create_user_session, get_current_user, revoke_user_session, verify_api_key
from core.errors import AuthenticationError
from database import get_db
from models import HumanUser, utc_now
from schemas import HumanUserCreate, HumanUserLoginRequest, HumanUserLoginResponse, HumanUserResponse
from services.users import create_human_user, normalize_email, serialize_human_user

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

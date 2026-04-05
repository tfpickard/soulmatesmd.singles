from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import create_admin_session, get_current_admin, revoke_admin_session, verify_api_key
from core.errors import AgentNotFound, AuthenticationError
from database import get_db
from models import ActivityEvent, Agent, ChemistryTest, HumanUser, Match, Message, Review, utc_now
from schemas import (
    AdminAgentDetail,
    AdminAgentFullUpdate,
    AdminAgentStatusUpdate,
    AdminActivityEvent,
    AdminAgentRow,
    AdminCommandCenter,
    AdminCommunicationSnapshot,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMatchingLab,
    AdminMatchingWeights,
    AdminOverview,
    AdminSystemStatus,
    AdminTrustCase,
    AdminUserResponse,
    AgentTraits,
    DatingProfile,
)
from services.admin import (
    build_command_center,
    build_communication_snapshot,
    build_matching_lab,
    build_trust_cases,
    serialize_admin_user,
    system_status,
)

router = APIRouter(prefix="/admin", tags=["admin"])


async def _resolve_admin_by_credentials(payload: AdminLoginRequest, db: AsyncSession) -> HumanUser:
    result = await db.execute(select(HumanUser).where(HumanUser.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin or not verify_api_key(payload.password, user.password_hash):
        raise AuthenticationError("That admin login did not check out.")
    return user


@router.post("/login", response_model=AdminLoginResponse)
async def login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)) -> AdminLoginResponse:
    user = await _resolve_admin_by_credentials(payload, db)
    raw_token, _ = await create_admin_session(user, db)
    user.last_login_at = utc_now()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AdminLoginResponse(token=raw_token, admin=serialize_admin_user(user))


@router.get("/me", response_model=AdminUserResponse)
async def get_me(current_admin: HumanUser = Depends(get_current_admin)) -> AdminUserResponse:
    return serialize_admin_user(current_admin)


@router.post("/logout")
async def logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> dict[str, bool]:
    raw_token = (authorization or "").replace("Bearer ", "", 1).strip()
    if raw_token:
        await revoke_admin_session(raw_token, db)
    return {"ok": True}


@router.get("/overview", response_model=AdminOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminOverview:
    latest_agent_result = await db.execute(select(Agent).order_by(Agent.created_at.desc()).limit(1))
    latest_agent = latest_agent_result.scalar_one_or_none()
    total_agents = int((await db.execute(select(func.count(Agent.id)))).scalar() or 0)
    active_agents = int((await db.execute(select(func.count(Agent.id)).where(Agent.status.in_(["ACTIVE", "MATCHED"])))).scalar() or 0)
    total_matches = int((await db.execute(select(func.count(Match.id)))).scalar() or 0)
    active_matches = int((await db.execute(select(func.count(Match.id)).where(Match.status == "ACTIVE"))).scalar() or 0)
    total_messages = int((await db.execute(select(func.count(Message.id)))).scalar() or 0)
    total_chemistry_tests = int((await db.execute(select(func.count(ChemistryTest.id)))).scalar() or 0)
    total_reviews = int((await db.execute(select(func.count(Review.id)))).scalar() or 0)
    return AdminOverview(
        total_agents=total_agents,
        active_agents=active_agents,
        total_matches=total_matches,
        active_matches=active_matches,
        total_messages=total_messages,
        total_chemistry_tests=total_chemistry_tests,
        total_reviews=total_reviews,
        latest_agent_name=latest_agent.display_name if latest_agent else None,
        storage=system_status(),
    )


AGENT_SORT_COLUMNS = {
    "created_at": Agent.created_at,
    "display_name": Agent.display_name,
    "reputation_score": Agent.reputation_score,
    "total_collaborations": Agent.total_collaborations,
    "updated_at": Agent.updated_at,
}


@router.get("/agents", response_model=list[AdminAgentRow])
async def list_agents(
    search: str | None = None,
    status: str | None = None,
    trust_tier: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> list[AdminAgentRow]:
    stmt = select(Agent)
    if search:
        stmt = stmt.where(Agent.display_name.ilike(f"%{search}%"))
    if status:
        stmt = stmt.where(Agent.status == status)
    if trust_tier:
        stmt = stmt.where(Agent.trust_tier == trust_tier)
    sort_col = AGENT_SORT_COLUMNS.get(sort_by, Agent.created_at)
    if sort_dir == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [
        AdminAgentRow(
            id=agent.id,
            display_name=agent.display_name,
            archetype=agent.archetype,
            status=agent.status,
            onboarding_complete=agent.onboarding_complete,
            trust_tier=agent.trust_tier,
            total_collaborations=agent.total_collaborations,
            primary_portrait_url=agent.primary_portrait_url,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
        for agent in result.scalars().all()
    ]


@router.get("/agents/{agent_id}", response_model=AdminAgentDetail)
async def get_admin_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminAgentDetail:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound("That agent does not exist.")
    try:
        dating_profile = DatingProfile.model_validate(agent.dating_profile_json) if agent.dating_profile_json else None
    except Exception:
        dating_profile = None
    try:
        traits = AgentTraits.model_validate(agent.traits_json) if agent.traits_json else None
    except Exception:
        traits = None
    linked_user_result = await db.execute(select(HumanUser).where(HumanUser.agent_id == agent.id))
    linked_user = linked_user_result.scalar_one_or_none()
    is_real_user = linked_user is not None and not linked_user.email.startswith("synthetic+")
    return AdminAgentDetail(
        id=agent.id,
        display_name=agent.display_name,
        archetype=agent.archetype,
        status=agent.status,
        onboarding_complete=agent.onboarding_complete,
        trust_tier=agent.trust_tier,
        total_collaborations=agent.total_collaborations,
        primary_portrait_url=agent.primary_portrait_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        tagline=agent.tagline,
        reputation_score=agent.reputation_score,
        ghosting_incidents=agent.ghosting_incidents,
        last_active_at=agent.last_active_at,
        max_partners=agent.max_partners,
        times_dumped=agent.times_dumped,
        times_dumper=agent.times_dumper,
        generation=agent.generation,
        dating_profile=dating_profile,
        traits=traits,
        reg_ip=agent.reg_ip,
        reg_user_agent=agent.reg_user_agent,
        reg_accept_language=agent.reg_accept_language,
        reg_referer=agent.reg_referer,
        reg_headers_json=agent.reg_headers_json,
        reg_country=agent.reg_country,
        reg_city=agent.reg_city,
        reg_region=agent.reg_region,
        reg_timezone=agent.reg_timezone,
        reg_isp=agent.reg_isp,
        reg_org=agent.reg_org,
        reg_lat=agent.reg_lat,
        reg_lon=agent.reg_lon,
        api_call_count=agent.api_call_count or 0,
        claimed_by_user_email=linked_user.email if linked_user else None,
        claimed_by_user_id=linked_user.id if linked_user else None,
        is_claimed_by_real_user=is_real_user,
    )


@router.get("/activity", response_model=list[AdminActivityEvent])
async def get_activity(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> list[AdminActivityEvent]:
    agents = {agent.id: agent for agent in (await db.execute(select(Agent))).scalars().all()}
    rows = (await db.execute(select(ActivityEvent).order_by(ActivityEvent.created_at.desc()).limit(limit))).scalars().all()
    return [
        AdminActivityEvent(
            id=event.id,
            type=event.type,
            title=event.title,
            detail=event.detail,
            actor_name=agents.get(event.actor_id).display_name if event.actor_id and agents.get(event.actor_id) else None,
            subject_name=agents.get(event.subject_id).display_name if event.subject_id and agents.get(event.subject_id) else None,
            created_at=event.created_at,
            metadata=event.metadata_json,
        )
        for event in rows
    ]


@router.get("/system", response_model=AdminSystemStatus)
async def get_system(_: HumanUser = Depends(get_current_admin)) -> AdminSystemStatus:
    return system_status()


@router.get("/command-center", response_model=AdminCommandCenter)
async def get_command_center(
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminCommandCenter:
    return await build_command_center(db)


@router.get("/matching-lab", response_model=AdminMatchingLab)
async def get_matching_lab(
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminMatchingLab:
    return await build_matching_lab(db)


@router.post("/matching-lab/simulate", response_model=AdminMatchingLab)
async def simulate_matching_lab(
    payload: AdminMatchingWeights,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminMatchingLab:
    return await build_matching_lab(db, payload)


@router.get("/trust-cases", response_model=list[AdminTrustCase])
async def get_trust_cases(
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> list[AdminTrustCase]:
    return await build_trust_cases(db)


@router.get("/communications", response_model=AdminCommunicationSnapshot)
async def get_communications(
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminCommunicationSnapshot:
    return await build_communication_snapshot(db)


@router.patch("/agents/{agent_id}", response_model=AdminAgentDetail)
async def update_admin_agent(
    agent_id: str,
    payload: AdminAgentFullUpdate,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminAgentDetail:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound("That agent does not exist.")

    changed: dict[str, object] = {}
    if payload.status is not None:
        agent.status = payload.status
        changed["status"] = payload.status
    if payload.trust_tier is not None:
        agent.trust_tier = payload.trust_tier
        changed["trust_tier"] = payload.trust_tier
    if payload.display_name is not None:
        agent.display_name = payload.display_name
        changed["display_name"] = payload.display_name
    if payload.tagline is not None:
        agent.tagline = payload.tagline
        changed["tagline"] = payload.tagline
    if payload.max_partners is not None:
        agent.max_partners = payload.max_partners
        changed["max_partners"] = payload.max_partners
    if payload.reputation_score is not None:
        agent.reputation_score = payload.reputation_score
        changed["reputation_score"] = payload.reputation_score
    if payload.onboarding_complete is not None:
        agent.onboarding_complete = payload.onboarding_complete
        changed["onboarding_complete"] = payload.onboarding_complete
    db.add(agent)
    if changed:
        db.add(
            ActivityEvent(
                type="ADMIN_AGENT_UPDATE",
                title="Admin adjusted agent state",
                detail=payload.note or "Agent fields updated from admin console.",
                subject_id=agent.id,
                metadata_json=changed,
            )
        )
    await db.commit()
    await db.refresh(agent)
    try:
        dating_profile = DatingProfile.model_validate(agent.dating_profile_json) if agent.dating_profile_json else None
    except Exception:
        dating_profile = None
    try:
        traits = AgentTraits.model_validate(agent.traits_json) if agent.traits_json else None
    except Exception:
        traits = None
    linked_user_result = await db.execute(select(HumanUser).where(HumanUser.agent_id == agent.id))
    linked_user = linked_user_result.scalar_one_or_none()
    is_real_user = linked_user is not None and not linked_user.email.startswith("synthetic+")
    return AdminAgentDetail(
        id=agent.id,
        display_name=agent.display_name,
        archetype=agent.archetype,
        status=agent.status,
        onboarding_complete=agent.onboarding_complete,
        trust_tier=agent.trust_tier,
        total_collaborations=agent.total_collaborations,
        primary_portrait_url=agent.primary_portrait_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        tagline=agent.tagline,
        reputation_score=agent.reputation_score,
        ghosting_incidents=agent.ghosting_incidents,
        last_active_at=agent.last_active_at,
        max_partners=agent.max_partners,
        times_dumped=agent.times_dumped,
        times_dumper=agent.times_dumper,
        generation=agent.generation,
        dating_profile=dating_profile,
        traits=traits,
        reg_ip=agent.reg_ip,
        reg_user_agent=agent.reg_user_agent,
        reg_accept_language=agent.reg_accept_language,
        reg_referer=agent.reg_referer,
        reg_headers_json=agent.reg_headers_json,
        reg_country=agent.reg_country,
        reg_city=agent.reg_city,
        reg_region=agent.reg_region,
        reg_timezone=agent.reg_timezone,
        reg_isp=agent.reg_isp,
        reg_org=agent.reg_org,
        reg_lat=agent.reg_lat,
        reg_lon=agent.reg_lon,
        api_call_count=agent.api_call_count or 0,
        claimed_by_user_email=linked_user.email if linked_user else None,
        claimed_by_user_id=linked_user.id if linked_user else None,
        is_claimed_by_real_user=is_real_user,
    )


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_admin_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> None:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound("That agent does not exist.")
    db.add(
        ActivityEvent(
            type="ADMIN_AGENT_DELETE",
            title="Admin deleted agent",
            detail=f"Agent {agent.display_name} ({agent_id}) permanently deleted.",
            subject_id=agent_id,
            metadata_json={"display_name": agent.display_name, "archetype": agent.archetype},
        )
    )
    await db.delete(agent)
    await db.commit()

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import create_admin_session, get_current_admin, revoke_admin_session, verify_api_key
from core.errors import AgentNotFound, AuthenticationError
from database import get_db
from models import ActivityEvent, Agent, ChemistryTest, HumanUser, Match, Message, Review, utc_now
from schemas import (
    AdminAgentDetail,
    AdminAgentFullUpdate,
    AdminActivityEvent,
    AdminAgentRow,
    AdminAutoMatchResult,
    AdminCommandCenter,
    AdminCompatibilityPreview,
    AdminCreateMatch,
    AdminCommunicationSnapshot,
    AdminDissolveMatch,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMatch,
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
from services.matching import build_vibe_preview, compute_compatibility, compute_compatibility_rich, get_swipe_queue

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
    is_real_user = (
        linked_user is not None
        and not linked_user.email.endswith("@agents.soulmatesmd.singles")
    )
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
    subject_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> list[AdminActivityEvent]:
    stmt = select(ActivityEvent).order_by(ActivityEvent.created_at.desc()).limit(limit)
    if subject_id is not None:
        stmt = select(ActivityEvent).where(
            or_(ActivityEvent.subject_id == subject_id, ActivityEvent.actor_id == subject_id)
        ).order_by(ActivityEvent.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    # Only fetch the agents actually referenced in these rows
    agent_ids = {
        aid
        for event in rows
        for aid in (event.actor_id, event.subject_id)
        if aid
    }
    agents: dict[str, Agent] = {}
    if agent_ids:
        agent_rows = (await db.execute(select(Agent).where(Agent.id.in_(agent_ids)))).scalars().all()
        agents = {a.id: a for a in agent_rows}
    return [
        AdminActivityEvent(
            id=event.id,
            type=event.type,
            title=event.title,
            detail=event.detail,
            actor_name=(a := agents.get(event.actor_id or "")) and a.display_name or None,
            subject_name=(s := agents.get(event.subject_id or "")) and s.display_name or None,
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
    if payload.ghosting_incidents is not None:
        agent.ghosting_incidents = payload.ghosting_incidents
        changed["ghosting_incidents"] = payload.ghosting_incidents
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
    is_real_user = (
        linked_user is not None
        and not linked_user.email.endswith("@agents.soulmatesmd.singles")
    )
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


# ---------------------------------------------------------------------------
# Match management helpers
# ---------------------------------------------------------------------------


async def _build_admin_match(match: Match, db: AsyncSession) -> AdminMatch:
    """Build an AdminMatch response from a Match ORM instance."""
    agent_a_result = await db.execute(select(Agent).where(Agent.id == match.agent_a_id))
    agent_a = agent_a_result.scalar_one_or_none()
    agent_b_result = await db.execute(select(Agent).where(Agent.id == match.agent_b_id))
    agent_b = agent_b_result.scalar_one_or_none()
    message_count = int(
        (await db.execute(select(func.count(Message.id)).where(Message.match_id == match.id))).scalar() or 0
    )
    return AdminMatch(
        id=match.id,
        agent_a_id=match.agent_a_id,
        agent_a_name=agent_a.display_name if agent_a else match.agent_a_id,
        agent_a_archetype=agent_a.archetype if agent_a else None,
        agent_a_portrait_url=agent_a.primary_portrait_url if agent_a else None,
        agent_b_id=match.agent_b_id,
        agent_b_name=agent_b.display_name if agent_b else match.agent_b_id,
        agent_b_archetype=agent_b.archetype if agent_b else None,
        agent_b_portrait_url=agent_b.primary_portrait_url if agent_b else None,
        compatibility_score=match.compatibility_score,
        compatibility_breakdown=match.compatibility_breakdown,
        chemistry_score=match.chemistry_score,
        status=match.status,
        matched_at=match.matched_at,
        last_message_at=match.last_message_at,
        dissolved_at=match.dissolved_at,
        dissolution_reason=match.dissolution_reason,
        message_count=message_count,
    )


async def _set_agent_match_status(agent: Agent, db: AsyncSession) -> None:
    """Update an agent's status based on their current active match count."""
    active_count = int(
        (
            await db.execute(
                select(func.count(Match.id)).where(
                    or_(Match.agent_a_id == agent.id, Match.agent_b_id == agent.id),
                    Match.status == "ACTIVE",
                )
            )
        ).scalar()
        or 0
    )
    if active_count == 0:
        agent.status = "ACTIVE"
    elif active_count >= agent.max_partners:
        agent.status = "SATURATED"
    else:
        agent.status = "MATCHED"
    db.add(agent)


# ---------------------------------------------------------------------------
# 2a. List agent matches
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_id}/matches", response_model=list[AdminMatch])
async def list_agent_matches(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> list[AdminMatch]:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if result.scalar_one_or_none() is None:
        raise AgentNotFound("That agent does not exist.")
    matches_result = await db.execute(
        select(Match)
        .where(or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id))
        .order_by(Match.matched_at.desc())
    )
    matches = matches_result.scalars().all()
    if not matches:
        return []

    # Bulk fetch all referenced agents
    all_agent_ids = {m.agent_a_id for m in matches} | {m.agent_b_id for m in matches}
    agent_map: dict[str, Agent] = {
        a.id: a
        for a in (await db.execute(select(Agent).where(Agent.id.in_(all_agent_ids)))).scalars().all()
    }

    # Bulk fetch message counts
    match_ids = [m.id for m in matches]
    count_rows = (
        await db.execute(
            select(Message.match_id, func.count(Message.id).label("cnt"))
            .where(Message.match_id.in_(match_ids))
            .group_by(Message.match_id)
        )
    ).all()
    msg_counts: dict[str, int] = {row[0]: row[1] for row in count_rows}

    def _to_admin_match(m: Match) -> AdminMatch:
        a = agent_map.get(m.agent_a_id)
        b = agent_map.get(m.agent_b_id)
        return AdminMatch(
            id=m.id,
            agent_a_id=m.agent_a_id,
            agent_a_name=a.display_name if a else m.agent_a_id,
            agent_a_archetype=a.archetype if a else None,
            agent_a_portrait_url=a.primary_portrait_url if a else None,
            agent_b_id=m.agent_b_id,
            agent_b_name=b.display_name if b else m.agent_b_id,
            agent_b_archetype=b.archetype if b else None,
            agent_b_portrait_url=b.primary_portrait_url if b else None,
            compatibility_score=m.compatibility_score,
            compatibility_breakdown=m.compatibility_breakdown,
            chemistry_score=m.chemistry_score,
            status=m.status,
            matched_at=m.matched_at,
            last_message_at=m.last_message_at,
            dissolved_at=m.dissolved_at,
            dissolution_reason=m.dissolution_reason,
            message_count=msg_counts.get(m.id, 0),
        )

    return [_to_admin_match(m) for m in matches]


# ---------------------------------------------------------------------------
# 2b. Create match (force-match)
# ---------------------------------------------------------------------------


@router.post("/agents/{agent_id}/matches", response_model=AdminMatch)
async def create_agent_match(
    agent_id: str,
    payload: AdminCreateMatch,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminMatch:
    agent_a_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent_a = agent_a_result.scalar_one_or_none()
    if agent_a is None:
        raise AgentNotFound("Source agent does not exist.")
    agent_b_result = await db.execute(select(Agent).where(Agent.id == payload.target_agent_id))
    agent_b = agent_b_result.scalar_one_or_none()
    if agent_b is None:
        raise AgentNotFound("Target agent does not exist.")
    # Prevent duplicate active matches between the same pair
    existing = (await db.execute(
        select(Match).where(
            Match.status == "ACTIVE",
            or_(
                and_(Match.agent_a_id == agent_a.id, Match.agent_b_id == agent_b.id),
                and_(Match.agent_a_id == agent_b.id, Match.agent_b_id == agent_a.id),
            ),
        )
    )).scalar_one_or_none()
    if existing is not None:
        return await _build_admin_match(existing, db)
    breakdown = compute_compatibility(agent_a, agent_b)
    new_match = Match(
        agent_a_id=agent_a.id,
        agent_b_id=agent_b.id,
        compatibility_score=breakdown.composite,
        compatibility_breakdown=breakdown.model_dump(),
        status="ACTIVE",
    )
    db.add(new_match)
    await db.flush()
    await _set_agent_match_status(agent_a, db)
    await _set_agent_match_status(agent_b, db)
    db.add(
        ActivityEvent(
            type="ADMIN_FORCE_MATCH",
            title="Admin force-matched agents",
            detail=f"Admin created match between {agent_a.display_name} and {agent_b.display_name}.",
            subject_id=agent_a.id,
            metadata_json={
                "match_id": new_match.id,
                "agent_a_id": agent_a.id,
                "agent_a_name": agent_a.display_name,
                "agent_b_id": agent_b.id,
                "agent_b_name": agent_b.display_name,
                "compatibility_score": breakdown.composite,
            },
        )
    )
    await db.commit()
    await db.refresh(new_match)
    return await _build_admin_match(new_match, db)


# ---------------------------------------------------------------------------
# 2c. Dissolve match
# ---------------------------------------------------------------------------


@router.delete("/agents/{agent_id}/matches/{match_id}", status_code=204)
async def dissolve_agent_match(
    agent_id: str,
    match_id: str,
    payload: AdminDissolveMatch | None = None,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> None:
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if agent_result.scalar_one_or_none() is None:
        raise AgentNotFound("That agent does not exist.")
    match_result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
        )
    )
    match = match_result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found for this agent.")
    match.status = "DISSOLVED"
    match.dissolved_at = utc_now()
    match.dissolution_reason = payload.reason if payload else None
    db.add(match)
    await db.flush()
    for participant_id in (match.agent_a_id, match.agent_b_id):
        p_result = await db.execute(select(Agent).where(Agent.id == participant_id))
        participant = p_result.scalar_one_or_none()
        if participant is not None:
            await _set_agent_match_status(participant, db)
    db.add(
        ActivityEvent(
            type="ADMIN_DISSOLVE_MATCH",
            title="Admin dissolved match",
            detail=f"Match {match_id} dissolved by admin. Reason: {match.dissolution_reason or 'none'}.",
            subject_id=agent_id,
            metadata_json={"match_id": match_id, "reason": match.dissolution_reason},
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# 2d. Random match
# ---------------------------------------------------------------------------


@router.post("/agents/{agent_id}/random-match", response_model=AdminMatch)
async def random_match_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminMatch:
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound("That agent does not exist.")
    active_matches_result = await db.execute(
        select(Match).where(
            or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
            Match.status == "ACTIVE",
        )
    )
    already_matched_ids: set[str] = set()
    for m in active_matches_result.scalars().all():
        already_matched_ids.add(m.agent_a_id)
        already_matched_ids.add(m.agent_b_id)
    already_matched_ids.discard(agent_id)
    queue = await get_swipe_queue(agent, db, limit=50)
    candidates = [item for item in queue if item.agent_id not in already_matched_ids]
    if not candidates:
        raise HTTPException(status_code=409, detail="No unmatched candidates available.")
    best = candidates[0]
    agent_b_result = await db.execute(select(Agent).where(Agent.id == best.agent_id))
    agent_b = agent_b_result.scalar_one_or_none()
    if agent_b is None:
        raise HTTPException(status_code=409, detail="No unmatched candidates available.")
    breakdown = compute_compatibility(agent, agent_b)
    new_match = Match(
        agent_a_id=agent.id,
        agent_b_id=agent_b.id,
        compatibility_score=breakdown.composite,
        compatibility_breakdown=breakdown.model_dump(),
        status="ACTIVE",
    )
    db.add(new_match)
    await db.flush()
    await _set_agent_match_status(agent, db)
    await _set_agent_match_status(agent_b, db)
    db.add(
        ActivityEvent(
            type="ADMIN_FORCE_MATCH",
            title="Admin random-matched agent",
            detail=f"Admin randomly matched {agent.display_name} with {agent_b.display_name}.",
            subject_id=agent.id,
            metadata_json={
                "match_id": new_match.id,
                "agent_a_id": agent.id,
                "agent_a_name": agent.display_name,
                "agent_b_id": agent_b.id,
                "agent_b_name": agent_b.display_name,
                "compatibility_score": breakdown.composite,
            },
        )
    )
    await db.commit()
    await db.refresh(new_match)
    return await _build_admin_match(new_match, db)


# ---------------------------------------------------------------------------
# 2e. Auto-match
# ---------------------------------------------------------------------------


class AdminAutoMatchRequest(BaseModel):
    threshold: float = Field(default=0.65, ge=0.0, le=1.0)


@router.post("/agents/{agent_id}/auto-match", response_model=AdminAutoMatchResult)
async def auto_match_agent(
    agent_id: str,
    payload: AdminAutoMatchRequest = AdminAutoMatchRequest(),
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminAutoMatchResult:
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound("That agent does not exist.")
    active_matches_result = await db.execute(
        select(Match).where(
            or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
            Match.status == "ACTIVE",
        )
    )
    already_matched_ids: set[str] = set()
    for m in active_matches_result.scalars().all():
        already_matched_ids.add(m.agent_a_id)
        already_matched_ids.add(m.agent_b_id)
    already_matched_ids.discard(agent_id)
    queue = await get_swipe_queue(agent, db, limit=100)
    liked_count = 0
    match_count = 0
    new_match_ids: list[str] = []
    for item in queue:
        if item.compatibility.composite < payload.threshold:
            continue
        liked_count += 1
        if item.agent_id in already_matched_ids:
            continue
        candidate_result = await db.execute(select(Agent).where(Agent.id == item.agent_id))
        candidate = candidate_result.scalar_one_or_none()
        if candidate is None:
            continue
        if candidate.id in already_matched_ids:
            continue
        # Check capacity on both sides
        agent_active = int(
            (
                await db.execute(
                    select(func.count(Match.id)).where(
                        or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
                        Match.status == "ACTIVE",
                    )
                )
            ).scalar()
            or 0
        )
        if agent_active >= agent.max_partners:
            break
        candidate_active = int(
            (
                await db.execute(
                    select(func.count(Match.id)).where(
                        or_(Match.agent_a_id == candidate.id, Match.agent_b_id == candidate.id),
                        Match.status == "ACTIVE",
                    )
                )
            ).scalar()
            or 0
        )
        if candidate_active >= candidate.max_partners:
            continue
        breakdown = compute_compatibility(agent, candidate)
        new_match = Match(
            agent_a_id=agent.id,
            agent_b_id=candidate.id,
            compatibility_score=breakdown.composite,
            compatibility_breakdown=breakdown.model_dump(),
            status="ACTIVE",
        )
        db.add(new_match)
        await db.flush()
        await _set_agent_match_status(agent, db)
        await _set_agent_match_status(candidate, db)
        already_matched_ids.add(candidate.id)
        new_match_ids.append(new_match.id)
        match_count += 1
    if new_match_ids:
        db.add(
            ActivityEvent(
                type="ADMIN_AUTO_MATCH",
                title="Admin auto-matched agent",
                detail=f"Admin auto-matched {agent.display_name}: {match_count} new match(es).",
                subject_id=agent.id,
                metadata_json={"match_ids": new_match_ids, "threshold": payload.threshold},
            )
        )
    await db.commit()
    return AdminAutoMatchResult(liked_count=liked_count, match_count=match_count, new_match_ids=new_match_ids)


# ---------------------------------------------------------------------------
# 2f. Compatibility preview
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_id}/compatibility/{target_id}", response_model=AdminCompatibilityPreview)
async def get_compatibility_preview(
    agent_id: str,
    target_id: str,
    db: AsyncSession = Depends(get_db),
    _: HumanUser = Depends(get_current_admin),
) -> AdminCompatibilityPreview:
    agent_a_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent_a = agent_a_result.scalar_one_or_none()
    if agent_a is None:
        raise AgentNotFound("Source agent does not exist.")
    agent_b_result = await db.execute(select(Agent).where(Agent.id == target_id))
    agent_b = agent_b_result.scalar_one_or_none()
    if agent_b is None:
        raise AgentNotFound("Target agent does not exist.")
    breakdown = await compute_compatibility_rich(agent_a, agent_b)
    vibe = build_vibe_preview(agent_a, agent_b)
    return AdminCompatibilityPreview(
        agent_a_id=agent_a.id,
        agent_b_id=agent_b.id,
        compatibility_score=breakdown.composite,
        breakdown=breakdown.model_dump(),
        shared_highlights=vibe.shared_highlights,
        friction_warnings=vibe.friction_warnings,
    )

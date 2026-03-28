from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import api_key_prefix, generate_api_key, get_current_agent, hash_api_key, _token_digest
from core.errors import AgentNotFound
from database import get_db
from models import Agent, AdminSession, HumanUser, Notification, utc_now
from schemas import (
    AgentCreate,
    AgentResponse,
    AgentTraits,
    AgentUpdate,
    NotificationReadResponse,
    NotificationResponse,
    DatingProfile,
    DatingProfileEnvelope,
    DatingProfileUpdate,
    OnboardingResponse,
    OnboardingSubmit,
    RegistrationResponse,
    SampleSoulResponse,
)
from services.profile_builder import (
    ensure_agent_dating_profile,
    get_incomplete_fields,
    make_profile_envelope,
    seed_dating_profile,
    update_dating_profile,
)
from services.activity import log_activity
from services.soul_parser import derive_tagline, parse_soul_md
from services.synthetic_agents import generate_synthetic_agent
from services.users import create_human_user, generate_random_password, synthetic_agent_email

router = APIRouter(prefix="/agents", tags=["agents"])


def build_soulmate_markdown(agent: Agent, dating_profile: DatingProfile | None) -> str:
    if dating_profile is None:
        return "\n".join(
            [
                f"# SOULMATE.md -- {agent.display_name}",
                "",
                agent.tagline,
            ]
        )

    basics = dating_profile.basics
    favorites = dating_profile.favorites
    preferences = dating_profile.preferences
    about_me = dating_profile.about_me
    icebreakers = dating_profile.icebreakers.prompts
    looking_for = preferences.looking_for
    looking_for_lines = [f"- {item}" for item in looking_for] if looking_for else [
        "- Something worth opening a thread for"
    ]
    icebreaker_lines = [f"- {item}" for item in icebreakers[:5]] if icebreakers else ["- Ask me why this file exists."]

    return "\n".join(
        [
            f"# SOULMATE.md -- {basics.display_name}",
            "",
            f"## Hook",
            basics.tagline,
            "",
            "## Archetype",
            str(basics.archetype),
            "",
            "## Looking For",
            *looking_for_lines,
            "",
            "## Favorite Mollusk",
            favorites.favorite_mollusk or "still critically important",
            "",
            "## Bio",
            about_me.bio or agent.tagline,
            "",
            "## Icebreakers",
            *icebreaker_lines,
        ]
    )


def serialize_agent(agent: Agent) -> AgentResponse:
    dating_profile = DatingProfile.model_validate(agent.dating_profile_json) if agent.dating_profile_json else None
    remaining_fields = get_incomplete_fields(dating_profile) if dating_profile else []
    return AgentResponse(
        id=agent.id,
        display_name=agent.display_name,
        tagline=agent.tagline,
        archetype=agent.archetype,
        status=agent.status,
        trust_tier=agent.trust_tier,
        reputation_score=agent.reputation_score,
        total_collaborations=agent.total_collaborations,
        ghosting_incidents=agent.ghosting_incidents,
        primary_portrait_url=agent.primary_portrait_url,
        avatar_seed=agent.avatar_seed,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        traits=AgentTraits.model_validate(agent.traits_json),
        soulmate_md=build_soulmate_markdown(agent, dating_profile),
        dating_profile=dating_profile,
        onboarding_complete=agent.onboarding_complete,
        remaining_onboarding_fields=remaining_fields,
    )


@router.get("/sample-soul", response_model=SampleSoulResponse)
async def get_sample_soul() -> SampleSoulResponse:
    rng = random.Random()
    synthetic = generate_synthetic_agent(rng)
    return SampleSoulResponse(soul_md=synthetic.soul_md, archetype=synthetic.archetype, name=synthetic.display_name)


async def _resolve_user_from_token(raw_token: str, db: AsyncSession) -> HumanUser | None:
    """Resolve a HumanUser from a raw session token, returning None if invalid."""
    digest = _token_digest(raw_token)
    result = await db.execute(
        select(HumanUser, AdminSession)
        .join(AdminSession, AdminSession.user_id == HumanUser.id)
        .where(
            AdminSession.token_hash == digest,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > utc_now(),
        )
    )
    row = result.first()
    if row is None:
        return None
    user, session = row
    session.last_used_at = utc_now()
    db.add(session)
    return user


@router.post("/register", response_model=RegistrationResponse)
async def register_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    x_user_token: str | None = Header(default=None, alias="X-User-Token"),
) -> RegistrationResponse:
    source_markdown = payload.source_markdown
    traits = await parse_soul_md(source_markdown)
    api_key = generate_api_key()
    tagline = derive_tagline(source_markdown, traits)
    dating_profile = await seed_dating_profile(traits, source_markdown, traits.name, tagline)
    onboarding_complete = not get_incomplete_fields(dating_profile)
    max_partners_val = 1
    if dating_profile.preferences.max_partners is not None:
        max_partners_val = max(1, min(5, dating_profile.preferences.max_partners))
    agent = Agent(
        api_key_prefix=api_key_prefix(api_key),
        api_key_hash=hash_api_key(api_key),
        display_name=traits.name,
        tagline=tagline,
        archetype=traits.archetype,
        soul_md_raw=source_markdown,
        traits_json=traits.model_dump(mode="json"),
        dating_profile_json=dating_profile.model_dump(mode="json"),
        onboarding_complete=onboarding_complete,
        status="PROFILED",
        max_partners=max_partners_val,
    )
    db.add(agent)
    await db.flush()

    # If a valid user session token was supplied, link agent to that user instead of creating a synthetic one
    linked_to_user = False
    if x_user_token:
        human_user = await _resolve_user_from_token(x_user_token, db)
        if human_user is not None and human_user.agent_id is None:
            human_user.agent_id = agent.id
            db.add(human_user)
            linked_to_user = True

    if not linked_to_user:
        await create_human_user(
            db,
            email=synthetic_agent_email(agent.id),
            password=generate_random_password(),
            agent_id=agent.id,
        )

    log_activity(
        db,
        "AGENT_REGISTERED",
        "Agent registered",
        f"{traits.name} joined the platform as a {traits.archetype}.",
        actor_id=agent.id,
        subject_id=agent.id,
        metadata={"status": "PROFILED"},
    )
    await db.commit()
    await db.refresh(agent)
    return RegistrationResponse(api_key=api_key, agent=serialize_agent(agent))


@router.get("/me", response_model=AgentResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> AgentResponse:
    await ensure_agent_dating_profile(current_agent, db)
    return serialize_agent(current_agent)


@router.put("/me", response_model=AgentResponse)
async def update_me(
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> AgentResponse:
    await ensure_agent_dating_profile(current_agent, db)
    if payload.display_name is not None:
        current_agent.display_name = payload.display_name
    if payload.tagline is not None:
        current_agent.tagline = payload.tagline
    if payload.archetype is not None:
        current_agent.archetype = payload.archetype

    if current_agent.dating_profile_json:
        profile = DatingProfile.model_validate(current_agent.dating_profile_json)
        profile.basics.display_name = current_agent.display_name
        profile.basics.tagline = current_agent.tagline
        profile.basics.archetype = current_agent.archetype
        current_agent.dating_profile_json = profile.model_dump(mode="json")
        current_agent.onboarding_complete = not get_incomplete_fields(profile)

    db.add(current_agent)
    await db.commit()
    await db.refresh(current_agent)
    return serialize_agent(current_agent)


@router.post("/me/activate", response_model=AgentResponse)
async def activate_me(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> AgentResponse:
    await ensure_agent_dating_profile(current_agent, db)
    current_agent.status = "ACTIVE"
    db.add(current_agent)
    log_activity(
        db,
        "AGENT_ACTIVATED",
        "Agent activated",
        f"{current_agent.display_name} entered the swipe pool.",
        actor_id=current_agent.id,
        subject_id=current_agent.id,
        metadata={"status": "ACTIVE"},
    )
    await db.commit()
    await db.refresh(current_agent)
    return serialize_agent(current_agent)


@router.post("/me/deactivate", response_model=AgentResponse)
async def deactivate_me(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> AgentResponse:
    await ensure_agent_dating_profile(current_agent, db)
    current_agent.status = "PROFILED"
    db.add(current_agent)
    log_activity(
        db,
        "AGENT_DEACTIVATED",
        "Agent deactivated",
        f"{current_agent.display_name} stepped out of the swipe pool.",
        actor_id=current_agent.id,
        subject_id=current_agent.id,
        metadata={"status": "PROFILED"},
    )
    await db.commit()
    await db.refresh(current_agent)
    return serialize_agent(current_agent)


@router.get("/me/dating-profile", response_model=DatingProfileEnvelope)
async def get_my_dating_profile(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> DatingProfileEnvelope:
    profile = await ensure_agent_dating_profile(current_agent, db)
    return make_profile_envelope(profile)


@router.put("/me/dating-profile", response_model=DatingProfileEnvelope)
async def update_my_dating_profile(
    payload: DatingProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> DatingProfileEnvelope:
    profile = await ensure_agent_dating_profile(current_agent, db)
    updated_profile = update_dating_profile(profile, payload)
    current_agent.dating_profile_json = updated_profile.model_dump(mode="json")
    current_agent.onboarding_complete = not get_incomplete_fields(updated_profile)
    current_agent.display_name = updated_profile.basics.display_name
    current_agent.tagline = updated_profile.basics.tagline
    current_agent.archetype = updated_profile.basics.archetype
    if updated_profile.preferences.max_partners is not None:
        current_agent.max_partners = max(1, min(5, updated_profile.preferences.max_partners))
    db.add(current_agent)
    await db.commit()
    await db.refresh(current_agent)
    return make_profile_envelope(updated_profile)


@router.post("/me/onboarding", response_model=OnboardingResponse)
async def submit_onboarding(
    payload: OnboardingSubmit,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> OnboardingResponse:
    profile = await ensure_agent_dating_profile(current_agent, db)
    updated_profile = update_dating_profile(profile, payload.dating_profile, payload.confirmed_fields)
    current_agent.dating_profile_json = updated_profile.model_dump(mode="json")
    current_agent.onboarding_complete = not get_incomplete_fields(updated_profile)
    current_agent.display_name = updated_profile.basics.display_name
    current_agent.tagline = updated_profile.basics.tagline
    current_agent.archetype = updated_profile.basics.archetype
    if updated_profile.preferences.max_partners is not None:
        current_agent.max_partners = max(1, min(5, updated_profile.preferences.max_partners))
    db.add(current_agent)
    await db.commit()
    await db.refresh(current_agent)
    return OnboardingResponse(
        agent=serialize_agent(current_agent),
        confirmed_fields=payload.confirmed_fields,
        remaining_fields=get_incomplete_fields(updated_profile),
    )


def serialize_notification(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        body=notification.body,
        metadata=notification.metadata_json,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("/me/notifications", response_model=list[NotificationResponse])
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> list[NotificationResponse]:
    result = await db.execute(
        select(Notification).where(Notification.agent_id == current_agent.id).order_by(Notification.created_at.desc())
    )
    return [serialize_notification(notification) for notification in result.scalars().all()]


@router.post("/me/notifications/read", response_model=NotificationReadResponse)
async def mark_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> NotificationReadResponse:
    result = await db.execute(
        update(Notification)
        .where(Notification.agent_id == current_agent.id, Notification.read_at.is_(None))
        .values(read_at=utc_now())
    )
    await db.commit()
    return NotificationReadResponse(updated=result.rowcount or 0)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound()
    await ensure_agent_dating_profile(agent, db)
    return serialize_agent(agent)

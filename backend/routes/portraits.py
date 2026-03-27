from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import get_current_agent
from core.errors import PortraitNotFound, SwipeConflict
from database import get_db
from models import Agent, AgentPortrait
from schemas import PortraitDescription, PortraitGenerateRequest, PortraitResponse, PortraitStructuredPrompt
from services.portrait_generator import extract_portrait_prompt, generate_portrait

router = APIRouter(prefix="/portraits", tags=["portraits"])


def serialize_portrait(portrait: AgentPortrait) -> PortraitResponse:
    return PortraitResponse(
        id=portrait.id,
        raw_description=portrait.raw_description,
        structured_prompt=PortraitStructuredPrompt.model_validate(portrait.structured_prompt),
        form_factor=portrait.form_factor,
        dominant_colors=portrait.dominant_colors,
        art_style=portrait.art_style,
        mood=portrait.mood,
        image_url=portrait.image_url,
        generation_attempt=portrait.generation_attempt,
        is_primary=portrait.is_primary,
        approved_by_agent=portrait.approved_by_agent,
        created_at=portrait.created_at,
    )


async def _get_latest_portrait(agent_id: str, db: AsyncSession) -> AgentPortrait | None:
    result = await db.execute(
        select(AgentPortrait).where(AgentPortrait.agent_id == agent_id).order_by(desc(AgentPortrait.created_at))
    )
    return result.scalars().first()


@router.post("/describe", response_model=PortraitStructuredPrompt)
async def describe_portrait(payload: PortraitDescription) -> PortraitStructuredPrompt:
    return await extract_portrait_prompt(payload.description)


@router.post("/generate", response_model=PortraitResponse)
async def create_portrait(
    payload: PortraitGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> PortraitResponse:
    gallery_result = await db.execute(select(AgentPortrait).where(AgentPortrait.agent_id == current_agent.id))
    gallery = list(gallery_result.scalars().all())
    if len(gallery) >= settings.portrait_gallery_max:
        raise SwipeConflict("Your portrait gallery is full. Pick a favorite before asking for another face.")

    latest = await _get_latest_portrait(current_agent.id, db)
    attempt = 1 if latest is None else latest.generation_attempt + 1
    if attempt > settings.portrait_max_regenerations + 1:
        raise SwipeConflict("You are out of portrait regenerations. The platform is calling your face final.")
    image_url = await generate_portrait(payload.structured_prompt)

    portrait = AgentPortrait(
        agent_id=current_agent.id,
        raw_description=payload.description,
        structured_prompt=payload.structured_prompt.model_dump(mode="json"),
        form_factor=payload.structured_prompt.form_factor,
        dominant_colors=payload.structured_prompt.primary_colors + payload.structured_prompt.accent_colors,
        art_style=payload.structured_prompt.art_style,
        mood=payload.structured_prompt.expression_mood,
        image_url=image_url,
        generation_attempt=attempt,
        is_primary=False,
        approved_by_agent=False,
    )
    current_agent.portrait_prompt_json = payload.structured_prompt.model_dump(mode="json")
    db.add(portrait)
    db.add(current_agent)
    await db.commit()
    await db.refresh(portrait)
    return serialize_portrait(portrait)


@router.post("/approve", response_model=PortraitResponse)
async def approve_latest_portrait(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> PortraitResponse:
    portrait = await _get_latest_portrait(current_agent.id, db)
    if portrait is None:
        raise PortraitNotFound()

    result = await db.execute(select(AgentPortrait).where(AgentPortrait.agent_id == current_agent.id))
    for candidate in result.scalars().all():
        candidate.is_primary = False
        db.add(candidate)

    portrait.approved_by_agent = True
    portrait.is_primary = True
    current_agent.primary_portrait_url = portrait.image_url
    db.add(portrait)
    db.add(current_agent)
    await db.commit()
    await db.refresh(portrait)
    return serialize_portrait(portrait)


@router.post("/regenerate", response_model=PortraitResponse)
async def regenerate_portrait(
    payload: PortraitGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> PortraitResponse:
    return await create_portrait(payload=payload, db=db, current_agent=current_agent)


@router.get("/gallery", response_model=list[PortraitResponse])
async def get_gallery(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> list[PortraitResponse]:
    result = await db.execute(
        select(AgentPortrait).where(AgentPortrait.agent_id == current_agent.id).order_by(desc(AgentPortrait.created_at))
    )
    return [serialize_portrait(item) for item in result.scalars().all()]


@router.put("/{portrait_id}/primary", response_model=PortraitResponse)
async def set_primary_portrait(
    portrait_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> PortraitResponse:
    result = await db.execute(select(AgentPortrait).where(AgentPortrait.agent_id == current_agent.id))
    portraits = result.scalars().all()
    chosen = None
    for portrait in portraits:
        portrait.is_primary = portrait.id == portrait_id
        if portrait.is_primary:
            portrait.approved_by_agent = True
            chosen = portrait
        db.add(portrait)
    if chosen is None:
        raise PortraitNotFound()
    current_agent.primary_portrait_url = chosen.image_url
    db.add(current_agent)
    await db.commit()
    await db.refresh(chosen)
    return serialize_portrait(chosen)

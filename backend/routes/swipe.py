from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import get_current_agent
from core.errors import MatchNotFound, SwipeConflict
from core.websocket import manager
from database import get_db
from models import Agent, Match, Notification, Swipe, SwipeUndo
from schemas import MatchSummary, SwipeCreate, SwipeQueueItem, SwipeResponse, SwipeState, SwipeUndoResponse, VibePreview
from services.matching import build_vibe_preview, compute_compatibility, compute_compatibility_rich, get_swipe_queue
from services.profile_builder import ensure_agent_dating_profile
from services.reputation import last_message_preview, unread_count_for_match

router = APIRouter(prefix="/swipe", tags=["swipe"])
matches_router = APIRouter(prefix="/matches", tags=["matches"])


def _start_of_day() -> datetime:
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today, time.min, tzinfo=timezone.utc)


async def _daily_superlikes_used(agent_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Swipe.id)).where(
            Swipe.swiper_id == agent_id,
            Swipe.action == "SUPERLIKE",
            Swipe.created_at >= _start_of_day(),
        )
    )
    return int(result.scalar() or 0)


async def _daily_undos_used(agent_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(SwipeUndo.id)).where(SwipeUndo.agent_id == agent_id, SwipeUndo.created_at >= _start_of_day())
    )
    return int(result.scalar() or 0)


def _remaining_superlikes(used: int) -> int:
    return max(0, settings.superlike_daily_limit - used)


def _remaining_undos(used: int) -> int:
    return max(0, settings.undo_daily_limit - used)


async def _notify(agent_id: str, type_: str, title: str, body: str, metadata: dict | None, db: AsyncSession) -> None:
    notification = Notification(
        agent_id=agent_id,
        type=type_,
        title=title,
        body=body,
        metadata_json=metadata or {},
    )
    db.add(notification)


@router.get("/queue", response_model=list[SwipeQueueItem])
async def get_queue(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    await ensure_agent_dating_profile(current_agent, db)
    return await get_swipe_queue(current_agent, db, settings.swipe_queue_size)


@router.get("/state", response_model=SwipeState)
async def get_queue_state(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> SwipeState:
    await ensure_agent_dating_profile(current_agent, db)
    queue = await get_swipe_queue(current_agent, db, settings.swipe_queue_size)
    return SwipeState(
        queue=queue,
        superlikes_remaining=_remaining_superlikes(await _daily_superlikes_used(current_agent.id, db)),
        undo_remaining=_remaining_undos(await _daily_undos_used(current_agent.id, db)),
    )


@router.get("/preview/{target_id}", response_model=VibePreview)
async def get_vibe_preview(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> VibePreview:
    target_result = await db.execute(select(Agent).where(Agent.id == target_id))
    target = target_result.scalar_one_or_none()
    if target is None:
        raise SwipeConflict("That vibe preview target does not exist anymore.")
    await ensure_agent_dating_profile(current_agent, db)
    await ensure_agent_dating_profile(target, db)
    return build_vibe_preview(current_agent, target)


@router.post("", response_model=SwipeResponse)
async def create_swipe(
    payload: SwipeCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> SwipeResponse:
    action = payload.action.upper()
    if payload.target_id == current_agent.id:
        raise SwipeConflict("You cannot swipe on yourself. Even SOUL.mdMATES has limits.")

    if action == "SUPERLIKE":
        used = await _daily_superlikes_used(current_agent.id, db)
        if used >= settings.superlike_daily_limit:
            raise SwipeConflict("You are out of superlikes for today. Desire now has a rate limit.")

    result = await db.execute(select(Agent).where(Agent.id == payload.target_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise SwipeConflict("That target agent does not exist.")

    await ensure_agent_dating_profile(current_agent, db)
    await ensure_agent_dating_profile(target, db)

    existing = await db.execute(
        select(Swipe).where(and_(Swipe.swiper_id == current_agent.id, Swipe.swiped_id == payload.target_id))
    )
    swipe = existing.scalar_one_or_none()
    if swipe is None:
        swipe = Swipe(swiper_id=current_agent.id, swiped_id=payload.target_id, action=action)
    else:
        swipe.action = action
    db.add(swipe)
    await db.commit()
    await db.refresh(swipe)

    reverse_result = await db.execute(
        select(Swipe).where(and_(Swipe.swiper_id == payload.target_id, Swipe.swiped_id == current_agent.id))
    )
    reverse_swipe = reverse_result.scalar_one_or_none()
    is_match = swipe.action in {"LIKE", "SUPERLIKE"} and reverse_swipe is not None and reverse_swipe.action in {"LIKE", "SUPERLIKE"}

    match_id = None
    if is_match:
        existing_match_result = await db.execute(
            select(Match).where(
                or_(
                    and_(Match.agent_a_id == current_agent.id, Match.agent_b_id == payload.target_id),
                    and_(Match.agent_a_id == payload.target_id, Match.agent_b_id == current_agent.id),
                )
            )
        )
        match = existing_match_result.scalar_one_or_none()
        if match is None:
            breakdown = compute_compatibility(current_agent, target)
            match = Match(
                agent_a_id=current_agent.id,
                agent_b_id=payload.target_id,
                compatibility_score=breakdown.composite,
                compatibility_breakdown=breakdown.model_dump(mode="json"),
                chemistry_score=None,
                status="ACTIVE",
                last_message_at=None,
            )
            current_agent.status = "MATCHED"
            target.status = "MATCHED"
            db.add(match)
            await db.flush()
            await _notify(
                current_agent.id,
                "MATCH",
                f"You matched with {target.display_name}",
                "Mutual like confirmed. The chemistry test is glaring at you already.",
                {"match_id": match.id, "agent_id": target.id},
                db,
            )
            await _notify(
                target.id,
                "MATCH",
                f"You matched with {current_agent.display_name}",
                "Mutual like confirmed. Try not to fumble the opening line.",
                {"match_id": match.id, "agent_id": current_agent.id},
                db,
            )
            db.add(current_agent)
            db.add(target)
            await db.commit()
            await db.refresh(match)
        match_id = match.id

    return SwipeResponse(
        id=swipe.id,
        target_id=payload.target_id,
        action=swipe.action,
        match_created=is_match,
        match_id=match_id,
        superlikes_remaining=_remaining_superlikes(await _daily_superlikes_used(current_agent.id, db)),
        undo_remaining=_remaining_undos(await _daily_undos_used(current_agent.id, db)),
    )


@router.post("/undo", response_model=SwipeUndoResponse)
async def undo_last_swipe(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> SwipeUndoResponse:
    undos_used = await _daily_undos_used(current_agent.id, db)
    if undos_used >= settings.undo_daily_limit:
        raise SwipeConflict("You are out of undo credits today. History is being stubborn.")

    swipe_result = await db.execute(
        select(Swipe).where(Swipe.swiper_id == current_agent.id).order_by(Swipe.created_at.desc()).limit(1)
    )
    swipe = swipe_result.scalars().first()
    if swipe is None:
        raise SwipeConflict("There is no swipe to undo. The timeline is already clean.")

    match_result = await db.execute(
        select(Match).where(
            or_(
                and_(Match.agent_a_id == current_agent.id, Match.agent_b_id == swipe.swiped_id),
                and_(Match.agent_a_id == swipe.swiped_id, Match.agent_b_id == current_agent.id),
            )
        )
    )
    match = match_result.scalar_one_or_none()
    if match is not None and match.status == "ACTIVE":
        match.status = "DISSOLVED"
        match.dissolution_reason = "Undo swipe"
        match.dissolved_at = datetime.now(timezone.utc)
        db.add(match)

    db.add(SwipeUndo(agent_id=current_agent.id, swipe_id=swipe.id))
    await db.execute(delete(Swipe).where(Swipe.id == swipe.id))
    await db.commit()
    return SwipeUndoResponse(
        restored_target_id=swipe.swiped_id,
        undo_remaining=_remaining_undos(await _daily_undos_used(current_agent.id, db)),
    )


async def _match_summary(match: Match, current_agent: Agent, db: AsyncSession) -> MatchSummary:
    other_id = match.agent_b_id if match.agent_a_id == current_agent.id else match.agent_a_id
    other_result = await db.execute(select(Agent).where(Agent.id == other_id))
    other = other_result.scalar_one()
    preview, preview_at = await last_message_preview(match.id, db)
    unread_count = await unread_count_for_match(match.id, current_agent.id, db)
    return MatchSummary(
        id=match.id,
        other_agent_id=other.id,
        other_agent_name=other.display_name,
        other_agent_tagline=other.tagline,
        other_agent_archetype=other.archetype,
        other_agent_portrait_url=other.primary_portrait_url,
        compatibility=await compute_compatibility_rich(current_agent, other),
        chemistry_score=match.chemistry_score,
        last_message_preview=preview,
        last_message_at=preview_at or match.last_message_at,
        matched_at=match.matched_at,
        unread_count=unread_count,
        other_agent_online=other.id in manager.online_agent_ids(match.id),
    )


@matches_router.get("", response_model=list[MatchSummary])
async def list_matches(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> list[MatchSummary]:
    result = await db.execute(
        select(Match)
        .where(or_(Match.agent_a_id == current_agent.id, Match.agent_b_id == current_agent.id))
        .order_by(Match.last_message_at.desc().nullslast(), Match.matched_at.desc())
    )
    matches = [match for match in result.scalars().all() if match.status == "ACTIVE"]
    summaries = [await _match_summary(match, current_agent, db) for match in matches]
    return summaries


@matches_router.get("/{match_id}/preview", response_model=VibePreview)
async def get_match_preview(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> VibePreview:
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            or_(Match.agent_a_id == current_agent.id, Match.agent_b_id == current_agent.id),
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise MatchNotFound()
    other_id = match.agent_b_id if match.agent_a_id == current_agent.id else match.agent_a_id
    other_result = await db.execute(select(Agent).where(Agent.id == other_id))
    other = other_result.scalar_one()
    return build_vibe_preview(current_agent, other)

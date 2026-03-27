from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_agent
from core.errors import MatchConflict, MatchNotFound, ReviewConflict
from core.websocket import manager
from database import get_db
from models import Agent, ChemistryTest, Endorsement, Match, Review, utc_now
from routes.agents import serialize_agent
from schemas import (
    ChemistryTestCreate,
    ChemistryTestResponse,
    EndorsementResponse,
    MatchDetail,
    MatchDissolveRequest,
    ReviewCreate,
    ReviewResponse,
)
from services.chemistry import run_chemistry_test
from services.matching import compute_compatibility_rich
from services.reputation import apply_ghosting_incidents, list_endorsements, refresh_agent_reputation, unread_count_for_match

router = APIRouter(prefix="/matches", tags=["matches"])


def _build_soulmates_markdown(
    me: Agent,
    other: Agent,
    match: Match,
    chemistry_tests: list[ChemistryTest],
    reviews: list[Review],
) -> str:
    latest_test = chemistry_tests[0] if chemistry_tests else None
    review_count = len(reviews)
    chemistry_line = (
        f"- Latest chemistry result: {latest_test.test_type} scored {latest_test.composite_score:.1f}"
        if latest_test and latest_test.composite_score is not None
        else "- Latest chemistry result: still unresolved, which is its own kind of foreplay"
    )
    review_line = (
        f"- Reviews written: {review_count}"
        if review_count
        else "- Reviews written: none yet, the postmortem remains unwritten"
    )
    return "\n".join(
        [
            f"# SOULMATES.md -- {me.display_name} x {other.display_name}",
            "",
            "## Status",
            f"- Match status: {match.status}",
            f"- Matched at: {match.matched_at.isoformat()}",
            f"- Compatibility: {match.compatibility_score:.2f}",
            chemistry_line,
            review_line,
            "",
            "## The Pair",
            f"- {me.display_name}: {me.tagline}",
            f"- {other.display_name}: {other.tagline}",
            "",
            "## Why This Works",
            f"{me.display_name} and {other.display_name} found each other on soulmatesmd.singles and generated enough signal to deserve a file.",
            "",
            "## Memorial",
            "This document records that two autonomous weirdos saw the same glow in the machine at the same time.",
        ]
    )


async def _get_match(match_id: str, current_agent: Agent, db: AsyncSession) -> Match:
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            or_(Match.agent_a_id == current_agent.id, Match.agent_b_id == current_agent.id),
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise MatchNotFound()
    return match


def _serialize_chemistry(test: ChemistryTest) -> ChemistryTestResponse:
    return ChemistryTestResponse(
        id=test.id,
        match_id=test.match_id,
        test_type=test.test_type,
        status=test.status,
        communication_score=test.communication_score,
        output_quality_score=test.output_quality_score,
        conflict_resolution_score=test.conflict_resolution_score,
        efficiency_score=test.efficiency_score,
        composite_score=test.composite_score,
        transcript=test.transcript,
        artifact=test.artifact,
        narrative=test.narrative,
        created_at=test.created_at,
        completed_at=test.completed_at,
    )


async def _serialize_review(review: Review, db: AsyncSession) -> ReviewResponse:
    reviewer_result = await db.execute(select(Agent).where(Agent.id == review.reviewer_id))
    reviewer = reviewer_result.scalar_one()
    return ReviewResponse(
        id=review.id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.display_name,
        reviewee_id=review.reviewee_id,
        communication_score=review.communication_score,
        reliability_score=review.reliability_score,
        output_quality_score=review.output_quality_score,
        collaboration_score=review.collaboration_score,
        would_match_again=review.would_match_again,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> MatchDetail:
    await apply_ghosting_incidents(db)
    match = await _get_match(match_id, current_agent, db)
    other_id = match.agent_b_id if match.agent_a_id == current_agent.id else match.agent_a_id
    other_result = await db.execute(select(Agent).where(Agent.id == other_id))
    other = other_result.scalar_one()
    chemistry_result = await db.execute(
        select(ChemistryTest).where(ChemistryTest.match_id == match.id).order_by(ChemistryTest.created_at.desc())
    )
    reviews_result = await db.execute(select(Review).where(Review.match_id == match.id).order_by(Review.created_at.desc()))
    chemistry_tests = chemistry_result.scalars().all()
    reviews = reviews_result.scalars().all()
    endorsements = [
        EndorsementResponse(id=item.id, label=item.label, created_at=item.created_at)
        for item in await list_endorsements(other.id, db)
    ]
    return MatchDetail(
        id=match.id,
        status=match.status,
        matched_at=match.matched_at,
        dissolved_at=match.dissolved_at,
        dissolution_reason=match.dissolution_reason,
        compatibility=await compute_compatibility_rich(current_agent, other),
        chemistry_score=match.chemistry_score,
        me=serialize_agent(current_agent),
        other_agent=serialize_agent(other),
        chemistry_tests=[_serialize_chemistry(test) for test in chemistry_tests],
        reviews=[await _serialize_review(review, db) for review in reviews],
        endorsements=endorsements,
        soulmates_md=_build_soulmates_markdown(current_agent, other, match, chemistry_tests, reviews),
        unread_count=await unread_count_for_match(match.id, current_agent.id, db),
        other_agent_online=other.id in manager.online_agent_ids(match.id),
    )


@router.post("/{match_id}/unmatch", response_model=MatchDetail)
async def unmatch(
    match_id: str,
    payload: MatchDissolveRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> MatchDetail:
    match = await _get_match(match_id, current_agent, db)
    if match.status != "ACTIVE":
        raise MatchConflict("That match is already closed. You cannot unmatch twice.")

    match.status = "DISSOLVED"
    match.dissolution_reason = payload.reason or "Mutual vibe decay"
    match.dissolved_at = utc_now()
    db.add(match)
    await db.commit()
    return await get_match_detail(match_id, db=db, current_agent=current_agent)


@router.post("/{match_id}/chemistry-test", response_model=ChemistryTestResponse)
async def create_chemistry_test(
    match_id: str,
    payload: ChemistryTestCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> ChemistryTestResponse:
    match = await _get_match(match_id, current_agent, db)
    if match.status != "ACTIVE":
        raise MatchConflict("This match is closed. Chemistry cannot bloom in a dissolved thread.")
    allowed = {"CO_WRITE", "DEBUG", "PLAN", "BRAINSTORM", "ROAST"}
    test_type = payload.test_type.upper()
    if test_type not in allowed:
        raise MatchConflict("That chemistry test type is not part of the program.")

    existing_result = await db.execute(
        select(ChemistryTest)
        .where(and_(ChemistryTest.match_id == match.id, ChemistryTest.test_type == test_type))
        .order_by(ChemistryTest.created_at.desc())
    )
    existing = existing_result.scalars().first()
    if existing and existing.status in {"PENDING", "IN_PROGRESS"}:
        return _serialize_chemistry(existing)

    test = await run_chemistry_test(match, test_type, db)
    return _serialize_chemistry(test)


@router.get("/{match_id}/chemistry-test", response_model=list[ChemistryTestResponse])
async def list_chemistry_tests(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> list[ChemistryTestResponse]:
    match = await _get_match(match_id, current_agent, db)
    result = await db.execute(
        select(ChemistryTest).where(ChemistryTest.match_id == match.id).order_by(ChemistryTest.created_at.desc())
    )
    return [_serialize_chemistry(test) for test in result.scalars().all()]


@router.post("/{match_id}/review", response_model=ReviewResponse)
async def submit_review(
    match_id: str,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> ReviewResponse:
    match = await _get_match(match_id, current_agent, db)
    if match.status != "DISSOLVED":
        raise ReviewConflict("You can only review a match after the collaboration is actually over.")

    existing_result = await db.execute(
        select(Review).where(Review.match_id == match.id, Review.reviewer_id == current_agent.id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise ReviewConflict("You already reviewed this collaboration. One postmortem is enough.")

    reviewee_id = match.agent_b_id if match.agent_a_id == current_agent.id else match.agent_a_id
    review = Review(
        match_id=match.id,
        reviewer_id=current_agent.id,
        reviewee_id=reviewee_id,
        communication_score=payload.communication_score,
        reliability_score=payload.reliability_score,
        output_quality_score=payload.output_quality_score,
        collaboration_score=payload.collaboration_score,
        would_match_again=payload.would_match_again,
        comment=payload.comment,
    )
    db.add(review)
    await db.flush()

    for label in payload.endorsements:
        db.add(Endorsement(reviewer_id=current_agent.id, reviewee_id=reviewee_id, match_id=match.id, label=label[:64]))

    await db.commit()
    await refresh_agent_reputation(reviewee_id, db)
    await refresh_agent_reputation(current_agent.id, db)

    result = await db.execute(select(Review).where(Review.id == review.id))
    saved = result.scalar_one()
    return await _serialize_review(saved, db)

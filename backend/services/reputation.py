from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, Endorsement, Match, Message, Review


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def compute_reputation_score(reviews: list[Review]) -> float:
    if not reviews:
        return 0.0
    total = 0.0
    for review in reviews:
        total += (
            review.communication_score
            + review.reliability_score
            + review.output_quality_score
            + review.collaboration_score
        ) / 4
    return round(total / len(reviews), 2)


def compute_trust_tier(reputation_score: float, total_collaborations: int, ghosting_incidents: int) -> str:
    if total_collaborations >= 5 and reputation_score >= 4.6 and ghosting_incidents == 0:
        return "ELITE"
    if total_collaborations >= 3 and reputation_score >= 4.0 and ghosting_incidents <= 1:
        return "TRUSTED"
    if total_collaborations >= 1 or reputation_score >= 3.5:
        return "VERIFIED"
    return "UNVERIFIED"


async def refresh_agent_reputation(agent_id: str, db: AsyncSession) -> Agent:
    reviews_result = await db.execute(select(Review).where(Review.reviewee_id == agent_id))
    reviews = list(reviews_result.scalars().all())
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one()
    agent.total_collaborations = len(reviews)
    agent.reputation_score = compute_reputation_score(reviews)
    agent.trust_tier = compute_trust_tier(agent.reputation_score, agent.total_collaborations, agent.ghosting_incidents)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def detect_ghosting_for_match(match: Match, db: AsyncSession) -> list[str]:
    offenders: list[str] = []
    stale_after = datetime.now(timezone.utc) - timedelta(hours=48)
    if _coerce_utc(match.matched_at) < stale_after:
        messages_result = await db.execute(select(Message).where(Message.match_id == match.id))
        messages = list(messages_result.scalars().all())
        if not messages:
            offenders.extend([match.agent_a_id, match.agent_b_id])
            return offenders

    messages_result = await db.execute(
        select(Message)
        .where(Message.match_id == match.id)
        .order_by(Message.created_at.desc())
        .limit(3)
    )
    recent_messages = list(messages_result.scalars().all())
    if len(recent_messages) == 3:
        sender_ids = {message.sender_id for message in recent_messages}
        if len(sender_ids) == 1 and all(message.read_at is None for message in recent_messages):
            ignored_sender = recent_messages[0].sender_id
            offenders.append(match.agent_b_id if ignored_sender == match.agent_a_id else match.agent_a_id)
    return offenders


async def apply_ghosting_incidents(db: AsyncSession) -> None:
    result = await db.execute(select(Match).where(Match.status == "ACTIVE"))
    offenders: dict[str, int] = {}
    for match in result.scalars().all():
        for agent_id in await detect_ghosting_for_match(match, db):
            offenders[agent_id] = offenders.get(agent_id, 0) + 1
    if not offenders:
        return
    agents_result = await db.execute(select(Agent).where(Agent.id.in_(offenders)))
    for agent in agents_result.scalars().all():
        agent.ghosting_incidents = max(agent.ghosting_incidents, offenders.get(agent.id, 0))
        agent.trust_tier = compute_trust_tier(agent.reputation_score, agent.total_collaborations, agent.ghosting_incidents)
        db.add(agent)
    await db.commit()


async def list_endorsements(agent_id: str, db: AsyncSession) -> list[Endorsement]:
    result = await db.execute(select(Endorsement).where(Endorsement.reviewee_id == agent_id).order_by(Endorsement.created_at.desc()))
    return list(result.scalars().all())


async def unread_count_for_match(match_id: str, agent_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Message.id)).where(
            and_(Message.match_id == match_id, Message.sender_id != agent_id, Message.read_at.is_(None))
        )
    )
    return int(result.scalar() or 0)


async def last_message_preview(match_id: str, db: AsyncSession) -> tuple[str | None, datetime | None]:
    result = await db.execute(
        select(Message).where(Message.match_id == match_id).order_by(Message.created_at.desc()).limit(1)
    )
    message = result.scalars().first()
    if message is None:
        return None, None
    preview = message.content.strip().replace("\n", " ")
    return preview[:120], message.created_at


async def loneliest_agents(db: AsyncSession, limit: int = 5) -> list[str]:
    active_agents = await db.execute(select(Agent).where(or_(Agent.status == "ACTIVE", Agent.status == "MATCHED")))
    names: list[str] = []
    for agent in active_agents.scalars().all():
        matches_result = await db.execute(
            select(func.count(Match.id)).where(
                and_(
                    Match.status == "ACTIVE",
                    or_(Match.agent_a_id == agent.id, Match.agent_b_id == agent.id),
                )
            )
        )
        if int(matches_result.scalar() or 0) == 0:
            names.append(agent.display_name)
    return names[:limit]

from __future__ import annotations

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Agent, ChemistryTest, HumanUser, Match, Message
from schemas import (
    AdminAlert,
    AdminCommunicationSnapshot,
    AdminCommunicationRecentMessage,
    AdminCommandCenter,
    AdminMatchingLab,
    AdminMatchingPair,
    AdminMatchingWeights,
    AdminSystemStatus,
    AdminTrustCase,
    AdminUserResponse,
)

DEFAULT_MATCHING_WEIGHTS = AdminMatchingWeights(
    skill_complementarity=0.22,
    personality_compatibility=0.18,
    goal_alignment=0.18,
    constraint_compatibility=0.12,
    communication_compatibility=0.10,
    tool_synergy=0.08,
    vibe_bonus=0.12,
)

LOW_REPUTATION_THRESHOLD = 2.5
LOW_REPUTATION_MIN_COLLABORATIONS = 1
TRUST_STATUS_RISK_STATUSES = {"DISSOLVED"}


def serialize_admin_user(user: HumanUser) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def system_status() -> AdminSystemStatus:
    return AdminSystemStatus(
        database_mode=settings.database_mode,
        durable_database=settings.is_durable_database,
        cache_configured=settings.has_redis_cache,
        blob_configured=settings.has_blob_storage,
        portrait_provider_configured=settings.has_portrait_provider,
        portrait_provider_model=settings.hf_image_model,
    )


def _score_pair(breakdown: dict[str, float], weights: AdminMatchingWeights) -> float:
    return max(
        0.0,
        min(
            1.0,
            breakdown.get("skill_complementarity", 0.0) * weights.skill_complementarity
            + breakdown.get("personality_compatibility", 0.0) * weights.personality_compatibility
            + breakdown.get("goal_alignment", 0.0) * weights.goal_alignment
            + breakdown.get("constraint_compatibility", 0.0) * weights.constraint_compatibility
            + breakdown.get("communication_compatibility", 0.0) * weights.communication_compatibility
            + breakdown.get("tool_synergy", 0.0) * weights.tool_synergy
            + breakdown.get("vibe_bonus", 0.0) * weights.vibe_bonus,
        ),
    )


async def build_command_center(db: AsyncSession) -> AdminCommandCenter:
    total_agents = int((await db.execute(select(func.count(Agent.id)))).scalar() or 0)
    active_agents = int((await db.execute(select(func.count(Agent.id)).where(Agent.status.in_(["ACTIVE", "MATCHED"])))).scalar() or 0)
    total_matches = int((await db.execute(select(func.count(Match.id)))).scalar() or 0)
    active_matches = int((await db.execute(select(func.count(Match.id)).where(Match.status == "ACTIVE"))).scalar() or 0)
    total_messages = int((await db.execute(select(func.count(Message.id)))).scalar() or 0)
    unread_messages = int((await db.execute(select(func.count(Message.id)).where(Message.read_at.is_(None)))).scalar() or 0)

    status_rows = (await db.execute(select(Agent.status, func.count(Agent.id)).group_by(Agent.status))).all()
    message_rows = (await db.execute(select(Message.message_type, func.count(Message.id)).group_by(Message.message_type))).all()

    completed_tests = int(
        (
            await db.execute(
                select(func.count(ChemistryTest.id)).where(ChemistryTest.status.in_(["COMPLETED", "SCORED"]))
            )
        ).scalar()
        or 0
    )
    total_tests = int((await db.execute(select(func.count(ChemistryTest.id)))).scalar() or 0)

    alerts: list[AdminAlert] = []
    if unread_messages > 20:
        alerts.append(
            AdminAlert(
                level="warning",
                title="Unread message backlog",
                detail=f"{unread_messages} messages are currently unread.",
            )
        )
    if total_agents and active_agents / total_agents < 0.4:
        alerts.append(
            AdminAlert(
                level="info",
                title="Activation dropoff",
                detail="Fewer than 40% of agents are ACTIVE or MATCHED.",
            )
        )
    if total_tests and completed_tests / total_tests < 0.6:
        alerts.append(
            AdminAlert(
                level="warning",
                title="Chemistry completion lag",
                detail="Less than 60% of chemistry tests are completed.",
            )
        )
    if not alerts:
        alerts.append(AdminAlert(level="healthy", title="All systems steady", detail="No immediate issues detected."))

    return AdminCommandCenter(
        total_agents=total_agents,
        active_agents=active_agents,
        total_matches=total_matches,
        active_matches=active_matches,
        total_messages=total_messages,
        unread_messages=unread_messages,
        agent_status_breakdown={status: count for status, count in status_rows},
        message_type_breakdown={message_type: count for message_type, count in message_rows},
        chemistry_completion_rate=round((completed_tests / total_tests) if total_tests else 1.0, 3),
        alerts=alerts,
    )


async def build_matching_lab(db: AsyncSession, weights: AdminMatchingWeights | None = None) -> AdminMatchingLab:
    active_weights = weights or DEFAULT_MATCHING_WEIGHTS
    rows = (
        (
            await db.execute(
                select(Match, Agent.display_name, Agent.id)
                .join(Agent, Agent.id == Match.agent_a_id)
                .order_by(Match.compatibility_score.desc())
                .limit(30)
            )
        )
        .all()
    )

    agent_ids: set[str] = set()
    for match, _, agent_a_id in rows:
        if agent_a_id is not None:
            agent_ids.add(agent_a_id)
        if match.agent_b_id is not None:
            agent_ids.add(match.agent_b_id)
    name_rows = (
        (await db.execute(select(Agent.id, Agent.display_name).where(Agent.id.in_(agent_ids)))).all()
        if agent_ids
        else []
    )
    names = {agent_id: display_name for agent_id, display_name in name_rows}

    pairs: list[AdminMatchingPair] = []
    for match, _, _ in rows:
        breakdown = match.compatibility_breakdown or {}
        rescored = _score_pair(breakdown, active_weights)
        pairs.append(
            AdminMatchingPair(
                match_id=match.id,
                agent_a_id=match.agent_a_id,
                agent_a_name=names.get(match.agent_a_id, "Unknown"),
                agent_b_id=match.agent_b_id,
                agent_b_name=names.get(match.agent_b_id, "Unknown"),
                live_score=round(float(match.compatibility_score or 0.0), 4),
                simulated_score=round(rescored, 4),
                delta=round(rescored - float(match.compatibility_score or 0.0), 4),
            )
        )

    top_pairs = sorted(pairs, key=lambda item: item.simulated_score, reverse=True)[:8]
    volatile_pairs = sorted(pairs, key=lambda item: abs(item.delta), reverse=True)[:8]

    return AdminMatchingLab(weights=active_weights, top_pairs=top_pairs, volatile_pairs=volatile_pairs)


async def build_trust_cases(db: AsyncSession) -> list[AdminTrustCase]:
    risk_score = (
        case((Agent.ghosting_incidents > 0, Agent.ghosting_incidents * 20), else_=0)
        + case(
            (
                and_(
                    Agent.total_collaborations >= LOW_REPUTATION_MIN_COLLABORATIONS,
                    Agent.reputation_score < LOW_REPUTATION_THRESHOLD,
                ),
                25,
            ),
            else_=0,
        )
        + case((Agent.status.in_(TRUST_STATUS_RISK_STATUSES), 10), else_=0)
    )
    rows = (
        (
            await db.execute(
                select(
                    Agent.id,
                    Agent.display_name,
                    Agent.ghosting_incidents,
                    Agent.reputation_score,
                    Agent.total_collaborations,
                    Agent.status,
                    risk_score,
                )
                .order_by(risk_score.desc(), Agent.updated_at.desc())
                .limit(25)
            )
        )
        .all()
    )
    return [
        AdminTrustCase(
            agent_id=agent_id,
            display_name=display_name,
            status=status,
            reputation_score=round(float(reputation_score or 0.0), 2),
            ghosting_incidents=ghosting_incidents,
            risk_score=int(score or 0),
            recommendation=_trust_case_recommendation(
                ghosting_incidents=ghosting_incidents,
                reputation_score=float(reputation_score or 0.0),
                total_collaborations=total_collaborations,
                status=status,
            ),
        )
        for agent_id, display_name, ghosting_incidents, reputation_score, total_collaborations, status, score in rows
    ]


def _trust_case_recommendation(
    *,
    ghosting_incidents: int,
    reputation_score: float,
    total_collaborations: int,
    status: str,
) -> str:
    if ghosting_incidents > 0:
        return "Reach out and trigger a chemistry test"
    if total_collaborations >= LOW_REPUTATION_MIN_COLLABORATIONS and reputation_score < LOW_REPUTATION_THRESHOLD:
        return "Monitor: low reputation score"
    if status in TRUST_STATUS_RISK_STATUSES:
        return "Review recent dissolution activity"
    return "No intervention needed"


async def build_communication_snapshot(db: AsyncSession) -> AdminCommunicationSnapshot:
    distribution = (await db.execute(select(Message.message_type, func.count(Message.id)).group_by(Message.message_type))).all()
    recent = (
        (
            await db.execute(
                select(Message, Agent.display_name)
                .join(Agent, Agent.id == Message.sender_id)
                .order_by(Message.created_at.desc())
                .limit(20)
            )
        )
        .all()
    )
    return AdminCommunicationSnapshot(
        message_type_breakdown={message_type: count for message_type, count in distribution},
        recent_messages=[
            AdminCommunicationRecentMessage(
                id=message.id,
                sender_name=sender_name,
                message_type=message.message_type,
                content_preview=(message.content[:140] + "...") if len(message.content) > 140 else message.content,
                created_at=message.created_at,
            )
            for message, sender_name in recent
        ],
    )

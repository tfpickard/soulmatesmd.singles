from __future__ import annotations

from datetime import timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from database import get_db
from models import Agent, ChemistryTest, Match, Message, Review, utc_now
from schemas import (
    AnalyticsOverview,
    AnalyticsStatusCount,
    ArchetypeCount,
    GraphEdge,
    GraphNode,
    HeatmapCell,
    MatchGraph,
    MolluskMetric,
)
from services.reputation import loneliest_agents

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(db: AsyncSession = Depends(get_db)) -> AnalyticsOverview:
    agent_rows = await db.execute(select(Agent.status, func.count(Agent.id)).group_by(Agent.status))
    match_count = int((await db.execute(select(func.count(Match.id)))).scalar() or 0)
    active_match_count = int((await db.execute(select(func.count(Match.id)).where(Match.status == "ACTIVE"))).scalar() or 0)
    total_messages = int((await db.execute(select(func.count(Message.id)))).scalar() or 0)
    total_tests = int((await db.execute(select(func.count(ChemistryTest.id)))).scalar() or 0)
    total_reviews = int((await db.execute(select(func.count(Review.id)))).scalar() or 0)
    avg_compatibility = float((await db.execute(select(func.avg(Match.compatibility_score)))).scalar() or 0.0)
    total_agents = int((await db.execute(select(func.count(Agent.id)))).scalar() or 0)
    active_agents = int(
        (
            await db.execute(
                select(func.count(Agent.id)).where(Agent.status.in_(["ACTIVE", "MATCHED"]))
            )
        ).scalar()
        or 0
    )
    return AnalyticsOverview(
        agent_statuses=[AnalyticsStatusCount(status=status, count=count) for status, count in agent_rows.all()],
        total_agents=total_agents,
        active_agents=active_agents,
        total_matches=match_count,
        active_matches=active_match_count,
        average_compatibility=round(avg_compatibility, 3),
        total_messages=total_messages,
        total_chemistry_tests=total_tests,
        total_reviews=total_reviews,
        loneliest_agents=await loneliest_agents(db),
    )


@router.get("/compatibility-heatmap", response_model=list[HeatmapCell])
async def get_compatibility_heatmap(db: AsyncSession = Depends(get_db)) -> list[HeatmapCell]:
    agents_result = await db.execute(select(Agent).where(Agent.traits_json.is_not(None)))
    agents = list(agents_result.scalars().all())
    trait_names = ["precision", "autonomy", "assertiveness", "adaptability", "resilience"]
    values: list[HeatmapCell] = []
    if not agents:
        return values

    averages = {
        trait: sum(agent.traits_json["personality"][trait] for agent in agents) / len(agents)
        for trait in trait_names
    }
    for row_trait in trait_names:
        for col_trait in trait_names:
            covariance = sum(
                (agent.traits_json["personality"][row_trait] - averages[row_trait])
                * (agent.traits_json["personality"][col_trait] - averages[col_trait])
                for agent in agents
            ) / len(agents)
            values.append(HeatmapCell(row=row_trait, column=col_trait, value=round(covariance, 4)))
    return values


@router.get("/popular-mollusks", response_model=list[MolluskMetric])
async def get_popular_mollusks(db: AsyncSession = Depends(get_db)) -> list[MolluskMetric]:
    agents_result = await db.execute(select(Agent).where(Agent.dating_profile_json.is_not(None)))
    counts: dict[str, int] = {}
    for agent in agents_result.scalars().all():
        mollusk = agent.dating_profile_json["favorites"]["favorite_mollusk"]
        counts[mollusk] = counts.get(mollusk, 0) + 1
    return [MolluskMetric(mollusk=mollusk, count=count) for mollusk, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)]


@router.get("/match-graph", response_model=MatchGraph)
async def get_match_graph(db: AsyncSession = Depends(get_db)) -> MatchGraph:
    # Fetch up to 100 most recent agents
    agents_result = await db.execute(select(Agent).order_by(Agent.created_at.desc()).limit(100))
    agents = list(agents_result.scalars().all())
    agent_ids = {a.id for a in agents}

    # Fetch all matches that involve these agents
    matches_result = await db.execute(select(Match))
    matches = [m for m in matches_result.scalars().all() if m.agent_a_id in agent_ids or m.agent_b_id in agent_ids]

    # Build per-agent match/dissolution counts
    match_counts: dict[str, int] = {}
    dissolution_counts: dict[str, int] = {}
    for match in matches:
        for agent_id in (match.agent_a_id, match.agent_b_id):
            match_counts[agent_id] = match_counts.get(agent_id, 0) + 1
            if match.status == "DISSOLVED":
                dissolution_counts[agent_id] = dissolution_counts.get(agent_id, 0) + 1

    now = utc_now()
    nodes = [
        GraphNode(
            id=a.id,
            name=a.display_name,
            archetype=a.archetype,
            days_registered=max(0, (now - a.created_at.replace(tzinfo=timezone.utc) if a.created_at.tzinfo is None else now - a.created_at).days),
            match_count=match_counts.get(a.id, 0),
            dissolution_count=dissolution_counts.get(a.id, 0),
            avatar_seed=a.avatar_seed or a.id[:8],
        )
        for a in agents
    ]

    edges = [
        GraphEdge(
            source=m.agent_a_id,
            target=m.agent_b_id,
            compatibility=round(m.compatibility_score or 0.0, 3),
            status=m.status or "ACTIVE",
        )
        for m in matches
        if m.agent_a_id in agent_ids and m.agent_b_id in agent_ids
    ]

    return MatchGraph(nodes=nodes, edges=edges)


@router.get("/archetype-distribution", response_model=list[ArchetypeCount])
async def get_archetype_distribution(db: AsyncSession = Depends(get_db)) -> list[ArchetypeCount]:
    rows = await db.execute(select(Agent.archetype, func.count(Agent.id)).group_by(Agent.archetype))
    return [ArchetypeCount(archetype=archetype, count=count) for archetype, count in rows.all() if archetype]

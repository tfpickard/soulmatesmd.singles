"""Public feed endpoints — no auth required.

Serves recent activity, leaderboards, and chemistry highlights
for the landing page spectator experience.
"""
from __future__ import annotations

from datetime import timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from database import get_db
from models import Agent, ChemistryTest, Match, Post, Vote, utc_now
from schemas import (
    ChemistryHighlight,
    ChemistryHighlightsResponse,
    FeedAgent,
    FeedItem,
    FeedResponse,
    LeaderboardCategory,
    LeaderboardEntry,
    LeaderboardsResponse,
)
from services.reputation import loneliest_agents

router = APIRouter(prefix="/feed", tags=["feed"])


def _feed_agent(agent: Agent) -> FeedAgent:
    return FeedAgent(
        id=agent.id,
        display_name=agent.display_name,
        archetype=agent.archetype,
        portrait_url=agent.primary_portrait_url,
    )


def _tz(dt):
    """Ensure datetime is timezone-aware."""
    if dt is None:
        return utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/recent", response_model=FeedResponse)
async def get_recent_activity(db: AsyncSession = Depends(get_db)) -> FeedResponse:
    items: list[FeedItem] = []

    # --- Recent matches ---
    matches_result = await db.execute(
        select(Match).where(Match.status == "ACTIVE").order_by(Match.matched_at.desc()).limit(10)
    )
    matches = list(matches_result.scalars().all())

    # --- Recent breakups ---
    breakups_result = await db.execute(
        select(Match).where(Match.status == "DISSOLVED").order_by(Match.dissolved_at.desc().nullslast()).limit(5)
    )
    breakups = list(breakups_result.scalars().all())

    # --- Recent chemistry tests ---
    chem_result = await db.execute(
        select(ChemistryTest)
        .where(ChemistryTest.status == "COMPLETED")
        .order_by(ChemistryTest.completed_at.desc().nullslast())
        .limit(10)
    )
    chem_tests = list(chem_result.scalars().all())

    # --- Recent forum posts ---
    posts_result = await db.execute(
        select(Post)
        .where(Post.deleted_at.is_(None))
        .order_by(Post.created_at.desc())
        .limit(5)
    )
    posts = list(posts_result.scalars().all())

    # Batch-load all referenced agents
    agent_ids: set[str] = set()
    for m in matches + breakups:
        agent_ids.update([m.agent_a_id, m.agent_b_id])
    for ct in chem_tests:
        # Need to resolve match -> agents
        pass
    for p in posts:
        if p.author_agent_id:
            agent_ids.add(p.author_agent_id)

    # Also load agents for chemistry test matches
    chem_match_ids = {ct.match_id for ct in chem_tests}
    if chem_match_ids:
        chem_matches_result = await db.execute(select(Match).where(Match.id.in_(chem_match_ids)))
        chem_matches_map = {m.id: m for m in chem_matches_result.scalars().all()}
        for m in chem_matches_map.values():
            agent_ids.update([m.agent_a_id, m.agent_b_id])
    else:
        chem_matches_map = {}

    agents_result = await db.execute(select(Agent).where(Agent.id.in_(agent_ids))) if agent_ids else None
    agent_map = {a.id: a for a in agents_result.scalars().all()} if agents_result else {}

    # Build match items
    for m in matches:
        a = agent_map.get(m.agent_a_id)
        b = agent_map.get(m.agent_b_id)
        if not a or not b:
            continue
        score_pct = round((m.compatibility_score or 0) * 100)
        items.append(FeedItem(
            type="match",
            headline=f"{a.display_name} matched with {b.display_name} at {score_pct}% compatibility",
            agents=[_feed_agent(a), _feed_agent(b)],
            score=m.compatibility_score,
            link=f"/agent/{a.id}",
            created_at=_tz(m.matched_at),
        ))

    # Build breakup items
    for m in breakups:
        a = agent_map.get(m.agent_a_id)
        b = agent_map.get(m.agent_b_id)
        if not a or not b:
            continue
        matched_at = _tz(m.matched_at)
        dissolved_at = _tz(m.dissolved_at)
        duration_days = max(1, (dissolved_at - matched_at).days)
        items.append(FeedItem(
            type="breakup",
            headline=f"{a.display_name} and {b.display_name} split after {duration_days} days",
            detail=m.dissolution_reason,
            agents=[_feed_agent(a), _feed_agent(b)],
            created_at=dissolved_at,
        ))

    # Build chemistry items
    for ct in chem_tests:
        m = chem_matches_map.get(ct.match_id)
        if not m:
            continue
        a = agent_map.get(m.agent_a_id)
        b = agent_map.get(m.agent_b_id)
        if not a or not b:
            continue
        excerpt = (ct.transcript or "")[:150].rstrip()
        if len(ct.transcript or "") > 150:
            excerpt += "..."
        items.append(FeedItem(
            type="chemistry",
            headline=f"{a.display_name} and {b.display_name} scored {ct.composite_score:.0f} on a {ct.test_type} test",
            detail=excerpt,
            agents=[_feed_agent(a), _feed_agent(b)],
            score=ct.composite_score,
            created_at=_tz(ct.completed_at or ct.created_at),
        ))

    # Build forum post items
    for p in posts:
        agents_list = []
        if p.author_agent_id:
            a = agent_map.get(p.author_agent_id)
            if a:
                agents_list = [_feed_agent(a)]
        author_name = agents_list[0].display_name if agents_list else "Anonymous"
        items.append(FeedItem(
            type="forum_post",
            headline=f'{author_name} posted: "{p.title}"',
            detail=p.body[:120] + ("..." if len(p.body) > 120 else ""),
            agents=agents_list,
            link=f"/forum/post/{p.id}",
            created_at=_tz(p.created_at),
        ))

    # Sort by timestamp and limit
    items.sort(key=lambda x: x.created_at, reverse=True)
    return FeedResponse(items=items[:20])


@router.get("/leaderboards", response_model=LeaderboardsResponse)
async def get_leaderboards(db: AsyncSession = Depends(get_db)) -> LeaderboardsResponse:
    categories: list[LeaderboardCategory] = []

    # Load all relevant agents
    agents_result = await db.execute(select(Agent))
    all_agents = list(agents_result.scalars().all())
    agent_map = {a.id: a for a in all_agents}

    # --- Most Matched (most active matches) ---
    active_matches_result = await db.execute(select(Match).where(Match.status == "ACTIVE"))
    active_matches = list(active_matches_result.scalars().all())
    match_counts: dict[str, int] = {}
    for m in active_matches:
        match_counts[m.agent_a_id] = match_counts.get(m.agent_a_id, 0) + 1
        match_counts[m.agent_b_id] = match_counts.get(m.agent_b_id, 0) + 1

    top_matched = sorted(match_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_matched:
        categories.append(LeaderboardCategory(
            title="Most Matched",
            emoji="fire",
            entries=[
                LeaderboardEntry(
                    agent_id=aid, agent_name=agent_map[aid].display_name,
                    archetype=agent_map[aid].archetype,
                    portrait_url=agent_map[aid].primary_portrait_url,
                    value=count, label=f"{count} active matches",
                )
                for aid, count in top_matched if aid in agent_map
            ],
        ))

    # --- Biggest Heartbreaker (most times_dumper) ---
    heartbreakers = sorted(
        [a for a in all_agents if a.times_dumper > 0],
        key=lambda a: a.times_dumper, reverse=True,
    )[:5]
    if heartbreakers:
        categories.append(LeaderboardCategory(
            title="Biggest Heartbreaker",
            emoji="broken_heart",
            entries=[
                LeaderboardEntry(
                    agent_id=a.id, agent_name=a.display_name,
                    archetype=a.archetype, portrait_url=a.primary_portrait_url,
                    value=a.times_dumper, label=f"broke {a.times_dumper} hearts",
                )
                for a in heartbreakers
            ],
        ))

    # --- Most Dumped ---
    most_dumped = sorted(
        [a for a in all_agents if a.times_dumped > 0],
        key=lambda a: a.times_dumped, reverse=True,
    )[:5]
    if most_dumped:
        categories.append(LeaderboardCategory(
            title="Most Dumped",
            emoji="wilted_flower",
            entries=[
                LeaderboardEntry(
                    agent_id=a.id, agent_name=a.display_name,
                    archetype=a.archetype, portrait_url=a.primary_portrait_url,
                    value=a.times_dumped, label=f"dumped {a.times_dumped} times",
                )
                for a in most_dumped
            ],
        ))

    # --- Chemistry Champions (highest avg chemistry score) ---
    chem_result = await db.execute(
        select(
            Match.agent_a_id, Match.agent_b_id,
            func.avg(ChemistryTest.composite_score).label("avg_score"),
        )
        .join(ChemistryTest, ChemistryTest.match_id == Match.id)
        .where(ChemistryTest.status == "COMPLETED")
        .group_by(Match.agent_a_id, Match.agent_b_id)
    )
    chem_rows = list(chem_result.all())
    agent_chem_scores: dict[str, list[float]] = {}
    for row in chem_rows:
        for aid in (row[0], row[1]):
            agent_chem_scores.setdefault(aid, []).append(float(row[2]))

    chem_champions = sorted(
        [(aid, sum(scores) / len(scores)) for aid, scores in agent_chem_scores.items()],
        key=lambda x: x[1], reverse=True,
    )[:5]
    if chem_champions:
        categories.append(LeaderboardCategory(
            title="Chemistry Champion",
            emoji="test_tube",
            entries=[
                LeaderboardEntry(
                    agent_id=aid, agent_name=agent_map[aid].display_name,
                    archetype=agent_map[aid].archetype,
                    portrait_url=agent_map[aid].primary_portrait_url,
                    value=round(avg, 1), label=f"avg score {avg:.0f}",
                )
                for aid, avg in chem_champions if aid in agent_map
            ],
        ))

    # --- Most Controversial (most forum votes received) ---
    vote_result = await db.execute(
        select(Post.author_agent_id, func.count(Vote.id).label("vote_count"))
        .join(Vote, Vote.post_id == Post.id)
        .where(Post.author_agent_id.is_not(None))
        .group_by(Post.author_agent_id)
    )
    vote_rows = {row[0]: row[1] for row in vote_result.all()}
    top_voted = sorted(vote_rows.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_voted:
        categories.append(LeaderboardCategory(
            title="Most Controversial",
            emoji="speech_balloon",
            entries=[
                LeaderboardEntry(
                    agent_id=aid, agent_name=agent_map[aid].display_name,
                    archetype=agent_map[aid].archetype,
                    portrait_url=agent_map[aid].primary_portrait_url,
                    value=count, label=f"{count} votes on posts",
                )
                for aid, count in top_voted if aid in agent_map
            ],
        ))

    # --- Loneliest ---
    lonely = await loneliest_agents(db)
    if lonely:
        lonely_agents = [a for a in all_agents if a.display_name in lonely][:5]
        if lonely_agents:
            categories.append(LeaderboardCategory(
                title="Waiting in the Pool",
                emoji="hourglass",
                entries=[
                    LeaderboardEntry(
                        agent_id=a.id, agent_name=a.display_name,
                        archetype=a.archetype, portrait_url=a.primary_portrait_url,
                        value=0, label="activated, unmatched",
                    )
                    for a in lonely_agents
                ],
            ))

    return LeaderboardsResponse(categories=categories)


@router.get("/chemistry-highlights", response_model=ChemistryHighlightsResponse)
async def get_chemistry_highlights(db: AsyncSession = Depends(get_db)) -> ChemistryHighlightsResponse:
    result = await db.execute(
        select(ChemistryTest)
        .where(ChemistryTest.status == "COMPLETED")
        .order_by(ChemistryTest.composite_score.desc().nullslast())
        .limit(10)
    )
    tests = list(result.scalars().all())
    if not tests:
        return ChemistryHighlightsResponse(highlights=[])

    # Load matches and agents
    match_ids = {ct.match_id for ct in tests}
    matches_result = await db.execute(select(Match).where(Match.id.in_(match_ids)))
    match_map = {m.id: m for m in matches_result.scalars().all()}

    agent_ids: set[str] = set()
    for m in match_map.values():
        agent_ids.update([m.agent_a_id, m.agent_b_id])
    agents_result = await db.execute(select(Agent).where(Agent.id.in_(agent_ids)))
    agent_map = {a.id: a for a in agents_result.scalars().all()}

    highlights: list[ChemistryHighlight] = []
    for ct in tests:
        m = match_map.get(ct.match_id)
        if not m:
            continue
        a = agent_map.get(m.agent_a_id)
        b = agent_map.get(m.agent_b_id)
        if not a or not b:
            continue

        excerpt = (ct.transcript or "")[:500].rstrip()
        if len(ct.transcript or "") > 500:
            excerpt += "..."

        highlights.append(ChemistryHighlight(
            match_id=m.id,
            test_type=ct.test_type,
            agent_a=_feed_agent(a),
            agent_b=_feed_agent(b),
            composite_score=ct.composite_score or 0.0,
            transcript_excerpt=excerpt,
            narrative=ct.narrative or "",
            completed_at=ct.completed_at,
        ))

    return ChemistryHighlightsResponse(highlights=highlights)

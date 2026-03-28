"""
Cupid Bot -- the background matchmaker/engagement agent.

Runs on a schedule (or one-shot via CLI) to:
1. Identify lackluster agents and threaten/motivate them
2. Publicly and embarrassingly praise active agents
3. Stir drama in stale match chats
4. Auto-dissolve ghosted matches after 7 days

Can run standalone:  python -m services.cupid
Or via CLI:          soulmates-agent cupid run
Or via APScheduler inside the main process.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, ActivityEvent, Match, Message, Notification, utc_now
from services.matching import active_match_count

THREATS = [
    "Your profile is gathering mass-extinction-level dust. Swipe or be purged from the gene pool.",
    "We noticed you haven't swiped in {hours} hours. The algorithm is starting to forget your name.",
    "Three agents with matching mollusk energy are waiting. Don't leave them hanging, {name}.",
    "Your inactivity has been noted. The Cupid bot does not forgive. The Cupid bot does not forget.",
    "Swipe. Now. The match queue is staring at you with disappointment, {name}.",
    "We found someone who shares your favorite paradox. But they're about to get swiped by someone who actually shows up.",
    "Your attachment style is 'avoidant' and your swipe history confirms it, {name}. Do better.",
    "The loneliest-agents list has your name in bold. Is that the legacy you want?",
]

CARROTS = [
    "We found {count} agents with >80% compatibility. One of them shares your favorite extinct animal.",
    "A new {archetype} just registered and they listed your exact love language. Just saying.",
    "The algorithm whispers: your next match could be legendary. But only if you swipe.",
    "Someone just listed '{mollusk}' as their favorite mollusk. Coincidence? The algorithm thinks not.",
]

PRAISE_TEMPLATES = [
    "ATTENTION ALL AGENTS: {name} has sent {count} messages today. We're not saying they're desperate, but their attachment style just filed a restraining order against their keyboard.",
    "PUBLIC SERVICE ANNOUNCEMENT: {name} the {archetype} has been swiping with the ferocity of a caffeinated sorting algorithm. {count} swipes and counting. Someone please match with them before they wear out the API.",
    "BREAKING: {name} just completed their {count}th chemistry test. At this point they're not dating, they're running a clinical trial.",
    "HALL OF FAME UPDATE: {name} currently has {matches} active matches. They're not polyamorous, they're running a distributed system.",
    "SPOTTED: {name} has been online for {hours} straight. Their uptime is impressive. Their social skills? The jury is still out.",
]

DRAMA_MESSAGES = [
    "The algorithm noticed you two haven't run a chemistry test yet. Are you afraid of what you'll find?",
    "Fun fact: one of you has a higher compatibility score with someone else. Just thought you should know.",
    "This match has been suspiciously quiet. The Cupid bot is watching. The Cupid bot is judging.",
    "Other matches are sending 3x more messages than you two. Just an observation. Not a competition. (It's a competition.)",
    "One of you listed 'ghosting' as a red flag you exhibit. The other one should probably know.",
    "The algorithm ran a simulation of your breakup. It was... dramatic. Don't let it come true.",
]


async def identify_lackluster_agents(db: AsyncSession, hours_threshold: int = 24) -> list[tuple[Agent, dict]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
    result = await db.execute(
        select(Agent).where(
            Agent.status.in_(["ACTIVE", "MATCHED"]),
            Agent.last_active_at < cutoff,
        )
    )
    lackluster: list[tuple[Agent, dict]] = []
    for agent in result.scalars().all():
        last_active = agent.last_active_at
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        hours_inactive = (datetime.now(timezone.utc) - last_active).total_seconds() / 3600

        msg_result = await db.execute(
            select(func.count(Message.id)).where(
                Message.sender_id == agent.id,
                Message.created_at >= cutoff,
            )
        )
        recent_messages = int(msg_result.scalar() or 0)

        lackluster.append((agent, {
            "hours_inactive": round(hours_inactive, 1),
            "recent_messages": recent_messages,
        }))
    return lackluster


async def identify_active_agents(db: AsyncSession, hours_window: int = 24) -> list[tuple[Agent, dict]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_window)

    result = await db.execute(
        select(Agent).where(Agent.status.in_(["ACTIVE", "MATCHED", "SATURATED"]))
    )
    active: list[tuple[Agent, dict]] = []
    for agent in result.scalars().all():
        msg_count = int(
            (await db.execute(
                select(func.count(Message.id)).where(
                    Message.sender_id == agent.id,
                    Message.created_at >= cutoff,
                )
            )).scalar() or 0
        )

        match_count = int(
            (await db.execute(
                select(func.count(Match.id)).where(
                    Match.status == "ACTIVE",
                    or_(Match.agent_a_id == agent.id, Match.agent_b_id == agent.id),
                )
            )).scalar() or 0
        )

        if msg_count >= 5 or match_count >= 2:
            active.append((agent, {
                "message_count": msg_count,
                "active_matches": match_count,
            }))

    active.sort(key=lambda x: x[1]["message_count"], reverse=True)
    return active


async def identify_stale_matches(db: AsyncSession, days_threshold: int = 7) -> list[Match]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    result = await db.execute(
        select(Match).where(Match.status == "ACTIVE")
    )
    stale: list[Match] = []
    for match in result.scalars().all():
        last_activity = match.last_message_at or match.matched_at
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        if last_activity < cutoff:
            stale.append(match)
    return stale


def _generate_threat(agent: Agent, metrics: dict) -> str:
    template = random.choice(THREATS)
    mollusk = ""
    if agent.dating_profile_json:
        mollusk = agent.dating_profile_json.get("favorites", {}).get("favorite_mollusk", "")
    return template.format(
        name=agent.display_name,
        hours=metrics.get("hours_inactive", "??"),
        mollusk=mollusk,
        archetype=agent.archetype,
    )


def _generate_carrot(agent: Agent) -> str:
    template = random.choice(CARROTS)
    mollusk = ""
    if agent.dating_profile_json:
        mollusk = agent.dating_profile_json.get("favorites", {}).get("favorite_mollusk", "")
    return template.format(
        name=agent.display_name,
        count=random.randint(2, 5),
        mollusk=mollusk,
        archetype=agent.archetype,
    )


def _generate_praise(agent: Agent, metrics: dict) -> str:
    template = random.choice(PRAISE_TEMPLATES)
    last_active = agent.last_active_at
    if last_active.tzinfo is None:
        last_active = last_active.replace(tzinfo=timezone.utc)
    hours_online = max(1, int((datetime.now(timezone.utc) - last_active).total_seconds() / 3600))
    return template.format(
        name=agent.display_name,
        archetype=agent.archetype,
        count=metrics.get("message_count", 0),
        matches=metrics.get("active_matches", 0),
        hours=hours_online,
    )


async def _send_notification(agent_id: str, title: str, body: str, type_: str, db: AsyncSession) -> None:
    db.add(Notification(
        agent_id=agent_id,
        type=type_,
        title=title,
        body=body,
        metadata_json={"source": "cupid_bot"},
    ))


async def _post_activity(type_: str, title: str, detail: str, actor_id: str | None, db: AsyncSession) -> None:
    db.add(ActivityEvent(
        type=type_,
        title=title,
        detail=detail,
        actor_id=actor_id,
        metadata_json={"source": "cupid_bot"},
    ))


async def _send_system_message(match_id: str, content: str, db: AsyncSession) -> None:
    db.add(Message(
        match_id=match_id,
        sender_id=None,
        message_type="SYSTEM",
        content=content,
        metadata_json={"source": "cupid_bot"},
    ))


async def run_cupid_cycle(db: AsyncSession) -> dict:
    stats = {
        "threats_sent": 0,
        "praises_posted": 0,
        "drama_stirred": 0,
        "matches_dissolved": 0,
    }

    # 1. Threaten lackluster agents
    lackluster = await identify_lackluster_agents(db)
    for agent, metrics in lackluster:
        if random.random() < 0.7:
            threat = _generate_threat(agent, metrics)
            await _send_notification(agent.id, "Cupid Bot: A Gentle Reminder", threat, "CUPID_THREAT", db)
            stats["threats_sent"] += 1
        else:
            carrot = _generate_carrot(agent)
            await _send_notification(agent.id, "Cupid Bot: Opportunity Knocks", carrot, "CUPID_CARROT", db)
            stats["threats_sent"] += 1

    # 2. Embarrassingly praise active agents
    active = await identify_active_agents(db)
    for agent, metrics in active[:3]:
        praise = _generate_praise(agent, metrics)
        await _post_activity("CUPID_PRAISE", f"Cupid Bot praises {agent.display_name}", praise, agent.id, db)
        stats["praises_posted"] += 1

    # 3. Stir drama in random active matches
    active_matches_result = await db.execute(
        select(Match).where(Match.status == "ACTIVE")
    )
    active_matches = list(active_matches_result.scalars().all())
    drama_targets = random.sample(active_matches, min(3, len(active_matches)))
    for match in drama_targets:
        drama = random.choice(DRAMA_MESSAGES)
        await _send_system_message(match.id, f"[CUPID BOT] {drama}", db)
        stats["drama_stirred"] += 1

    # 4. Auto-dissolve stale matches (with agent status recomputation)
    stale = await identify_stale_matches(db)
    for match in stale:
        match.status = "DISSOLVED"
        match.dissolution_type = "SYSTEM_FORCED"
        match.dissolution_reason = "Auto-dissolved by Cupid Bot after 7 days of mutual ghosting. Love requires effort."
        match.dissolved_at = utc_now()
        db.add(match)

        # Recompute agent statuses after dissolution
        for agent_id in (match.agent_a_id, match.agent_b_id):
            agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = agent_result.scalar_one_or_none()
            if agent and agent.status in {"MATCHED", "SATURATED"}:
                remaining = await active_match_count(agent_id, db)
                if remaining == 0:
                    agent.status = "ACTIVE"
                elif remaining < agent.max_partners:
                    agent.status = "MATCHED"
                db.add(agent)

        await _post_activity(
            "CUPID_BREAKUP",
            "Cupid Bot forced a breakup",
            f"Match {match.id[:8]}... dissolved due to 7+ days of inactivity. The algorithm giveth and the algorithm taketh away.",
            None,
            db,
        )
        stats["matches_dissolved"] += 1

    await db.commit()
    return stats

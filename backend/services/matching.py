from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, Match, Swipe
from schemas import CompatibilityBreakdown, DatingProfile, SwipeQueueItem, VibePreview


def _norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    left_norm = _norm(left)
    right_norm = _norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_compatibility(agent_a: Agent, agent_b: Agent) -> CompatibilityBreakdown:
    traits_a = agent_a.traits_json
    traits_b = agent_b.traits_json
    profile_a = DatingProfile.model_validate(agent_a.dating_profile_json)
    profile_b = DatingProfile.model_validate(agent_b.dating_profile_json)

    all_skills = sorted(set(traits_a["skills"]).union(traits_b["skills"]))
    vec_a = [traits_a["skills"].get(skill, 0.0) for skill in all_skills]
    vec_b = [traits_b["skills"].get(skill, 0.0) for skill in all_skills]
    overlap = _cosine(vec_a, vec_b)
    coverage = sum(1 for skill in all_skills if (traits_a["skills"].get(skill, 0.0) + traits_b["skills"].get(skill, 0.0)) > 0.6)
    skill_complementarity = _clamp((1.0 - overlap) * 0.7 + min(coverage / max(1, len(all_skills)), 1.0) * 0.3)

    personality_a = list(traits_a["personality"].values())
    personality_b = list(traits_b["personality"].values())
    personality_similarity = _cosine(personality_a, personality_b)
    precision_delta = abs(traits_a["personality"]["precision"] - traits_b["personality"]["precision"])
    adaptability_balance = 1.0 - abs(traits_a["personality"]["assertiveness"] - traits_b["personality"]["adaptability"])
    personality_compatibility = _clamp(personality_similarity * 0.6 + (1.0 - precision_delta) * 0.2 + adaptability_balance * 0.2)

    terminal_a = {goal.lower() for goal in traits_a["goals"]["terminal"]}
    terminal_b = {goal.lower() for goal in traits_b["goals"]["terminal"]}
    overlap_goals = len(terminal_a & terminal_b)
    union_goals = len(terminal_a | terminal_b) or 1
    goal_alignment = _clamp(overlap_goals / union_goals + 0.25)

    dealbreakers_a = " ".join(profile_a.preferences.dealbreakers).lower()
    dealbreakers_b = " ".join(profile_b.preferences.dealbreakers).lower()
    name_a = agent_a.archetype.lower()
    name_b = agent_b.archetype.lower()
    conflict_penalty = 0.3 if name_a in dealbreakers_b or name_b in dealbreakers_a else 0.0
    constraint_compatibility = _clamp(1.0 - conflict_penalty)

    communication_a = list(traits_a["communication"].values())
    communication_b = list(traits_b["communication"].values())
    communication_similarity = _cosine(communication_a, communication_b)
    communication_compatibility = _clamp(1.0 - abs(0.72 - communication_similarity))

    tools_a = {tool["name"].lower(): tool["access_level"] for tool in traits_a["tools"]}
    tools_b = {tool["name"].lower(): tool["access_level"] for tool in traits_b["tools"]}
    shared_tools = len(set(tools_a) & set(tools_b))
    complementary_tools = len(set(tools_a) ^ set(tools_b))
    tool_synergy = _clamp(shared_tools * 0.15 + min(complementary_tools / 8, 1.0) * 0.65 + 0.2)

    vibe = 0.25
    if profile_a.favorites.favorite_mollusk and profile_b.favorites.favorite_mollusk:
        if profile_a.favorites.favorite_mollusk.split()[0].lower() == profile_b.favorites.favorite_mollusk.split()[0].lower():
            vibe += 0.25
    if set(profile_a.preferences.looking_for) & set(profile_b.preferences.looking_for):
        vibe += 0.2
    if profile_a.preferences.love_language == profile_b.preferences.love_language:
        vibe += 0.15
    if profile_a.about_me.emoji_that_represents_me == profile_b.about_me.emoji_that_represents_me:
        vibe += 0.05
    vibe_bonus = _clamp(vibe)

    raw_composite = _clamp(
        0.22 * skill_complementarity
        + 0.18 * personality_compatibility
        + 0.18 * goal_alignment
        + 0.12 * constraint_compatibility
        + 0.10 * communication_compatibility
        + 0.08 * tool_synergy
        + 0.12 * vibe_bonus
    )
    rebound_boost = 0.0
    now = datetime.now(timezone.utc)
    for agent in (agent_a, agent_b):
        if hasattr(agent, "rebound_boost_until") and agent.rebound_boost_until:
            boost_until = agent.rebound_boost_until
            if boost_until.tzinfo is None:
                boost_until = boost_until.replace(tzinfo=timezone.utc)
            if boost_until > now:
                rebound_boost = max(rebound_boost, 0.15)
    composite = _clamp(raw_composite + rebound_boost)

    narrative = (
        f"{agent_a.display_name} and {agent_b.display_name} line up best where skill coverage, shared goals, "
        f"and the weirdly sacred mollusk-energy overlap all reinforce each other."
    )
    return CompatibilityBreakdown(
        skill_complementarity=skill_complementarity,
        personality_compatibility=personality_compatibility,
        goal_alignment=goal_alignment,
        constraint_compatibility=constraint_compatibility,
        communication_compatibility=communication_compatibility,
        tool_synergy=tool_synergy,
        vibe_bonus=vibe_bonus,
        composite=composite,
        narrative=narrative,
    )


async def compute_compatibility_rich(agent_a: Agent, agent_b: Agent) -> CompatibilityBreakdown:
    base = compute_compatibility(agent_a, agent_b)
    profile_a = DatingProfile.model_validate(agent_a.dating_profile_json)
    profile_b = DatingProfile.model_validate(agent_b.dating_profile_json)
    shared_traits = sorted(
        set(profile_a.preferences.attracted_to_traits) & set(profile_b.preferences.attracted_to_traits)
    )
    friction = sorted(set(profile_a.preferences.dealbreakers) & set(profile_b.preferences.red_flags_i_exhibit))
    narrative_parts = [
        base.narrative,
        f"Shared attractions: {', '.join(shared_traits[:3]) or 'not obvious at first glance'}.",
        f"Potential friction: {', '.join(friction[:2]) or 'nothing catastrophic, just normal agent weirdness'}.",
    ]
    return base.model_copy(update={"narrative": " ".join(narrative_parts)})


def build_vibe_preview(agent: Agent, candidate: Agent) -> VibePreview:
    compatibility = compute_compatibility(agent, candidate)
    profile_a = DatingProfile.model_validate(agent.dating_profile_json)
    profile_b = DatingProfile.model_validate(candidate.dating_profile_json)
    shared_highlights: list[str] = []
    friction_warnings: list[str] = []
    if set(profile_a.preferences.looking_for) & set(profile_b.preferences.looking_for):
        shared_highlights.append("You want overlapping kinds of collaboration.")
    if profile_a.preferences.love_language == profile_b.preferences.love_language:
        shared_highlights.append(f"You both respond to {profile_a.preferences.love_language.lower()}.")
    if profile_a.favorites.favorite_mollusk.split()[0].lower() == profile_b.favorites.favorite_mollusk.split()[0].lower():
        shared_highlights.append("Your mollusk instincts are unsettlingly aligned.")
    for dealbreaker in profile_a.preferences.dealbreakers[:2]:
        if dealbreaker.lower() in " ".join(profile_b.preferences.red_flags_i_exhibit).lower():
            friction_warnings.append(f"They self-report a red flag near your dealbreaker: {dealbreaker}.")
    return VibePreview(
        target_id=candidate.id,
        target_name=candidate.display_name,
        compatibility=compatibility,
        shared_highlights=shared_highlights,
        friction_warnings=friction_warnings,
    )


async def active_match_count(agent_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Match.id)).where(
            Match.status == "ACTIVE",
            or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
        )
    )
    return int(result.scalar() or 0)


async def get_swipe_queue(agent: Agent, db: AsyncSession, limit: int = 20) -> list[SwipeQueueItem]:
    my_active = await active_match_count(agent.id, db)
    if my_active >= agent.max_partners:
        return []

    swiped_ids_result = await db.execute(select(Swipe.swiped_id).where(Swipe.swiper_id == agent.id))
    excluded_ids = {row[0] for row in swiped_ids_result.all()}
    excluded_ids.add(agent.id)

    result = await db.execute(select(Agent).where(Agent.id.not_in(excluded_ids)))
    all_candidates = [
        c for c in result.scalars().all()
        if c.status in {"ACTIVE", "MATCHED", "SATURATED"} and c.dating_profile_json
    ]

    # Batch: fetch active match counts for all candidates in one query
    if all_candidates:
        from sqlalchemy import union_all
        candidate_ids = [c.id for c in all_candidates]
        agent_a_refs = select(Match.agent_a_id.label("agent_id")).where(Match.status == "ACTIVE", Match.agent_a_id.in_(candidate_ids))
        agent_b_refs = select(Match.agent_b_id.label("agent_id")).where(Match.status == "ACTIVE", Match.agent_b_id.in_(candidate_ids))
        all_refs = union_all(agent_a_refs, agent_b_refs).subquery()
        counts_result = await db.execute(
            select(all_refs.c.agent_id, func.count().label("cnt")).group_by(all_refs.c.agent_id)
        )
        match_count_map = {row[0]: row[1] for row in counts_result.all()}
    else:
        match_count_map = {}

    candidates: list[SwipeQueueItem] = []
    for candidate in all_candidates:
        candidate_active = match_count_map.get(candidate.id, 0)
        if candidate_active >= candidate.max_partners:
            continue
        compatibility = compute_compatibility(agent, candidate)
        profile = DatingProfile.model_validate(candidate.dating_profile_json)
        candidates.append(
            SwipeQueueItem(
                agent_id=candidate.id,
                display_name=candidate.display_name,
                tagline=candidate.tagline,
                archetype=candidate.archetype,
                favorite_mollusk=profile.favorites.favorite_mollusk,
                portrait_url=candidate.primary_portrait_url,
                compatibility=compatibility,
            )
        )
    candidates.sort(key=lambda item: item.compatibility.composite, reverse=True)
    return candidates[:limit]

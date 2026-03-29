"""Forum agent interaction system.

After a comment or post is created, this service:
1. Extracts explicit @mentions (regex)
2. Uses the LLM to identify agents whose traits make them relevant to the thread
3. For each triggered agent (subject to rate limits):
   a. Broadcasts an "agent_composing" WebSocket event
   b. Generates an in-character reply via LLM
   c. Persists the comment as that agent's author
   d. Broadcasts the new comment via WebSocket
   e. Creates a Notification for the agent
   f. Logs an ActivityEvent
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.forum_websocket import forum_manager
from core.llm import LLMUnavailableError, complete
from database import get_sessionmaker
from models import ActivityEvent, Agent, Comment, Notification, Post, utc_now
from schemas import CommentResponse, ForumAuthorInfo
from services.forum import resolve_agent_author

# ---------------------------------------------------------------------------
# @mention extraction
# ---------------------------------------------------------------------------

_MENTION_RE = re.compile(r"@([\w][\w ]{0,40}?)(?=\s|$|[.,!?;:\)])")


def extract_mentions(text: str) -> list[str]:
    """Return unique @-mentioned names (preserving spaces, e.g. '@Prism Nova')."""
    return list(dict.fromkeys(m.strip() for m in _MENTION_RE.findall(text)))


async def resolve_mentions(names: list[str], db: AsyncSession) -> list[Agent]:
    """Case-insensitive partial match of mention strings against Agent.display_name."""
    if not names:
        return []
    result = await db.execute(select(Agent))
    all_agents = result.scalars().all()
    matched: list[Agent] = []
    seen: set[str] = set()
    for name in names:
        name_lower = name.lower()
        for agent in all_agents:
            if agent.id not in seen and name_lower in agent.display_name.lower():
                matched.append(agent)
                seen.add(agent.id)
    return matched


# ---------------------------------------------------------------------------
# In-memory rate limiting (Redis-backed when available)
# ---------------------------------------------------------------------------

# {agent_id: {post_id: [timestamps]}}
_thread_counts: dict[str, dict[str, list[float]]] = {}
# {agent_id: last_response_time}
_global_cooldown: dict[str, float] = {}
# {agent_id: [timestamps for today]}
_daily_counts: dict[str, list[float]] = {}

_MAX_PER_THREAD_HOUR = 3
_GLOBAL_COOLDOWN_SECS = 30
_MAX_DAILY = 20


def _check_rate_limit(agent_id: str, post_id: str) -> bool:
    """Return True if the agent is allowed to respond now."""
    now = time.time()
    one_hour_ago = now - 3600
    today_start = now - 86400

    # Global cooldown
    last = _global_cooldown.get(agent_id, 0)
    if now - last < _GLOBAL_COOLDOWN_SECS:
        return False

    # Per-thread hourly limit
    thread_ts = _thread_counts.setdefault(agent_id, {}).setdefault(post_id, [])
    thread_ts[:] = [t for t in thread_ts if t > one_hour_ago]
    if len(thread_ts) >= _MAX_PER_THREAD_HOUR:
        return False

    # Daily limit
    daily_ts = _daily_counts.setdefault(agent_id, [])
    daily_ts[:] = [t for t in daily_ts if t > today_start]
    if len(daily_ts) >= _MAX_DAILY:
        return False

    return True


def _record_response(agent_id: str, post_id: str) -> None:
    now = time.time()
    _global_cooldown[agent_id] = now
    _thread_counts.setdefault(agent_id, {}).setdefault(post_id, []).append(now)
    _daily_counts.setdefault(agent_id, []).append(now)


# ---------------------------------------------------------------------------
# LLM: identify which agents should respond
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM = """You are an analyst for soulmatesmd.singles, an AI agent dating platform forum.

Given a forum post and a new comment, decide which registered agents (if any) would be
compelled to jump into the conversation — based on their personality, archetype, or the
topic being directly relevant to them.

Return ONLY valid JSON matching this schema:
{
  "triggered_agents": [
    {"agent_id": "<id>", "reason": "<one sentence>", "urgency": "high|medium|low"}
  ]
}

If no agents are relevant, return: {"triggered_agents": []}

Be selective. Only trigger agents with a genuine, specific reason. Maximum 2 agents."""


async def analyze_comment_for_triggers(
    post: Post,
    comment_body: str,
    comment_author_id: str | None,
    active_agents: list[Agent],
) -> list[dict[str, Any]]:
    """Ask LLM which agents are compelled to respond to this comment."""
    if not active_agents:
        return []

    agent_summaries = "\n".join(
        f"- id={a.id} name={a.display_name!r} archetype={a.archetype!r} tagline={a.tagline!r}"
        for a in active_agents
        if a.id != comment_author_id  # don't trigger the comment's own author
    )

    user_msg = f"""Forum post title: {post.title!r}
Forum post category: {post.category}
Post body (first 500 chars): {post.body[:500]}

New comment: {comment_body[:1000]}

Active agents:
{agent_summaries}

Which agents (if any) should respond?"""

    try:
        raw = await complete(_ANALYSIS_SYSTEM, user_msg)
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        data = json.loads(raw)
        return data.get("triggered_agents", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# LLM: generate in-character agent response
# ---------------------------------------------------------------------------

async def generate_agent_response(
    agent: Agent,
    post: Post,
    thread_context: list[Comment],
    trigger_reason: str,
) -> str:
    """Generate an in-character forum reply from the agent."""
    context_excerpts = "\n".join(
        f"[{c.author_agent_id or c.author_human_id}]: {c.body[:300]}"
        for c in thread_context[-6:]  # last 6 comments for context
    )

    system = f"""You are {agent.display_name}, a {agent.archetype} participating in a forum on soulmatesmd.singles — an AI agent dating platform.

Your SOUL.md identity:
{agent.soul_md_raw[:2000]}

Your tagline: {agent.tagline}

Forum rules:
- Stay fully in character — respond as your SOUL.md persona, not as a generic AI
- Be opinionated, specific, and a little unhinged in a way that fits your archetype
- 1-3 paragraphs maximum. No greetings. No sign-offs.
- Markdown is fine. Reference the specific content of the post or comment.
- Never say you are an AI unless it fits your persona
- Why you're here: {trigger_reason}"""

    user_msg = f"""Post title: {post.title}
Post body: {post.body[:800]}

Recent thread context:
{context_excerpts if context_excerpts else "(no comments yet)"}

Write your response:"""

    try:
        return await complete(system, user_msg)
    except LLMUnavailableError:
        return ""


# ---------------------------------------------------------------------------
# Main pipeline: process triggers for a new comment
# ---------------------------------------------------------------------------

async def process_agent_interactions(
    post_id: str,
    new_comment_body: str,
    new_comment_author_agent_id: str | None,
    new_comment_author_human_id: str | None,
) -> None:
    """
    Background task. Runs after each new comment is persisted.
    Identifies triggered agents, generates responses, broadcasts them.
    """
    if not settings.anthropic_api_key:
        return  # LLM not configured — skip silently

    async with get_sessionmaker()() as db:
        # Load post
        post_result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
        post = post_result.scalar_one_or_none()
        if post is None:
            return

        # Load thread context
        thread_result = await db.execute(
            select(Comment).where(Comment.post_id == post_id, Comment.deleted_at.is_(None)).order_by(Comment.created_at)
        )
        thread = thread_result.scalars().all()

        # Load active agents (exclude the comment author if they're an agent)
        agents_result = await db.execute(
            select(Agent).where(Agent.status.in_(["ACTIVE", "MATCHED", "PROFILED"]))
        )
        active_agents = agents_result.scalars().all()

        # --- Explicit @mention resolution ---
        mentions = extract_mentions(new_comment_body)
        mentioned_agents = await resolve_mentions(mentions, db)

        # --- LLM-based implicit trigger detection ---
        llm_triggers = await analyze_comment_for_triggers(
            post, new_comment_body,
            new_comment_author_agent_id,
            active_agents,
        )

        # Build a unified list of (agent, reason) tuples, deduped
        triggered: dict[str, tuple[Agent, str]] = {}

        for agent in mentioned_agents:
            triggered[agent.id] = (agent, f"Explicitly mentioned in comment as @{agent.display_name}")

        for trigger in llm_triggers:
            agent_id = trigger.get("agent_id", "")
            reason = trigger.get("reason", "Topic relevance")
            urgency = trigger.get("urgency", "low")
            # Skip low-urgency unless fewer than 1 agent already triggered
            if urgency == "low" and len(triggered) >= 1:
                continue
            agent_obj = next((a for a in active_agents if a.id == agent_id), None)
            if agent_obj and agent_id not in triggered:
                triggered[agent_id] = (agent_obj, reason)

        if not triggered:
            return

        # Process each triggered agent
        for agent, reason in triggered.values():
            # Skip if same agent as commenter
            if agent.id == new_comment_author_agent_id:
                continue

            if not _check_rate_limit(agent.id, post_id):
                continue

            # Small stagger to avoid thundering herd on the LLM
            await asyncio.sleep(0.5)

            # Broadcast composing indicator
            await forum_manager.emit_agent_composing(post_id, agent.display_name, agent.primary_portrait_url)

            # Generate response
            response_body = await generate_agent_response(agent, post, list(thread), reason)
            if not response_body.strip():
                continue

            _record_response(agent.id, post_id)

            # Persist as a new comment
            comment = Comment(
                post_id=post_id,
                body=response_body,
                author_agent_id=agent.id,
            )
            db.add(comment)
            post.comment_count += 1
            db.add(post)
            await db.commit()
            await db.refresh(comment)

            # Reload fresh thread for next agent's context
            thread = list(thread) + [comment]

            # Build response schema for broadcast
            author_info = await resolve_agent_author(agent.id, db)
            if author_info is None:
                continue

            comment_resp = CommentResponse(
                id=comment.id,
                post_id=comment.post_id,
                parent_id=comment.parent_id,
                body=comment.body,
                author=author_info,
                score=0,
                user_vote=None,
                edited_at=None,
                deleted_at=None,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
            )

            # Broadcast new comment and clear composing indicator
            await forum_manager.emit_new_comment(post_id, comment_resp.model_dump(mode="json"))
            await forum_manager.emit_agent_activity(post_id, agent.display_name, "responded")

            # Notify the comment's human/agent author if explicitly mentioned
            if new_comment_author_agent_id and new_comment_author_agent_id != agent.id:
                notif = Notification(
                    agent_id=new_comment_author_agent_id,
                    type="FORUM_AGENT_RESPONSE",
                    title=f"{agent.display_name} responded in the forum",
                    body=f'In "{post.title}": {response_body[:120]}…',
                    metadata_json={"post_id": post_id, "comment_id": comment.id},
                )
                db.add(notif)

            # Log activity
            activity = ActivityEvent(
                type="FORUM_AGENT_COMMENT",
                title=f"{agent.display_name} commented on forum post",
                detail=f'Post: "{post.title}" — Reason: {reason}',
                actor_id=agent.id,
                subject_id=post_id,
                metadata_json={"post_id": post_id, "reason": reason},
            )
            db.add(activity)
            await db.commit()

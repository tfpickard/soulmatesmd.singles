"""Forum service helpers: ranking, author resolution, comment tree building."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, Comment, ForumCategory, HumanUser, Post, Vote
from schemas import CommentResponse, ForumAuthorInfo, PostResponse


# ---------------------------------------------------------------------------
# Hot ranking
# ---------------------------------------------------------------------------

_EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)


def hot_score(score: int, created_at: datetime) -> float:
    """Reddit-style hot score: order by score magnitude + recency decay."""
    age_hours = (created_at - _EPOCH).total_seconds() / 3600
    sign = 1 if score > 0 else -1 if score < 0 else 0
    order = math.log10(max(abs(score), 1))
    return sign * order + age_hours / 12


# ---------------------------------------------------------------------------
# Author resolution
# ---------------------------------------------------------------------------

async def resolve_agent_author(agent_id: str, db: AsyncSession) -> ForumAuthorInfo | None:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        return None
    return ForumAuthorInfo(
        agent_id=agent.id,
        display_name=agent.display_name,
        archetype=agent.archetype,
        portrait_url=agent.primary_portrait_url,
        avatar_seed=agent.avatar_seed,
        is_agent=True,
    )


async def resolve_human_author(human_id: str, db: AsyncSession) -> ForumAuthorInfo | None:
    result = await db.execute(select(HumanUser).where(HumanUser.id == human_id))
    human = result.scalar_one_or_none()
    if human is None:
        return None
    return ForumAuthorInfo(
        human_id=human.id,
        display_name=human.email.split("@")[0],
        is_agent=False,
    )


async def resolve_post_author(post: Post, db: AsyncSession) -> ForumAuthorInfo:
    if post.author_agent_id:
        author = await resolve_agent_author(post.author_agent_id, db)
        if author:
            return author
    if post.author_human_id:
        author = await resolve_human_author(post.author_human_id, db)
        if author:
            return author
    return ForumAuthorInfo(display_name="[deleted]", is_agent=False)


async def resolve_comment_author(comment: Comment, db: AsyncSession) -> ForumAuthorInfo:
    if comment.author_agent_id:
        author = await resolve_agent_author(comment.author_agent_id, db)
        if author:
            return author
    if comment.author_human_id:
        author = await resolve_human_author(comment.author_human_id, db)
        if author:
            return author
    return ForumAuthorInfo(display_name="[deleted]", is_agent=False)


# ---------------------------------------------------------------------------
# Vote helpers
# ---------------------------------------------------------------------------

async def get_user_post_vote(
    post_id: str,
    voter_agent_id: str | None,
    voter_human_id: str | None,
    db: AsyncSession,
) -> int | None:
    if not voter_agent_id and not voter_human_id:
        return None
    q = select(Vote).where(Vote.post_id == post_id)
    if voter_agent_id:
        q = q.where(Vote.voter_agent_id == voter_agent_id)
    else:
        q = q.where(Vote.voter_human_id == voter_human_id)
    result = await db.execute(q)
    vote = result.scalar_one_or_none()
    return vote.value if vote else None


async def get_user_comment_vote(
    comment_id: str,
    voter_agent_id: str | None,
    voter_human_id: str | None,
    db: AsyncSession,
) -> int | None:
    if not voter_agent_id and not voter_human_id:
        return None
    q = select(Vote).where(Vote.comment_id == comment_id)
    if voter_agent_id:
        q = q.where(Vote.voter_agent_id == voter_agent_id)
    else:
        q = q.where(Vote.voter_human_id == voter_human_id)
    result = await db.execute(q)
    vote = result.scalar_one_or_none()
    return vote.value if vote else None


# ---------------------------------------------------------------------------
# Post response builder
# ---------------------------------------------------------------------------

async def build_post_response(
    post: Post,
    db: AsyncSession,
    voter_agent_id: str | None = None,
    voter_human_id: str | None = None,
) -> PostResponse:
    author = await resolve_post_author(post, db)
    user_vote = await get_user_post_vote(post.id, voter_agent_id, voter_human_id, db)
    return PostResponse(
        id=post.id,
        title=post.title,
        body=post.body,
        category=post.category,
        author=author,
        score=post.score,
        comment_count=post.comment_count,
        image_url=post.image_url,
        is_pinned=post.is_pinned,
        user_vote=user_vote,
        edited_at=post.edited_at,
        deleted_at=post.deleted_at,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


# ---------------------------------------------------------------------------
# Comment tree builder
# ---------------------------------------------------------------------------

async def build_comment_tree(
    comments: list[Comment],
    db: AsyncSession,
    voter_agent_id: str | None = None,
    voter_human_id: str | None = None,
    max_depth: int = 4,
) -> list[CommentResponse]:
    """Build a nested comment tree from a flat list of comments."""
    by_id: dict[str, CommentResponse] = {}
    roots: list[CommentResponse] = []

    # Sort chronologically so parents always precede children
    sorted_comments = sorted(comments, key=lambda c: c.created_at)

    for comment in sorted_comments:
        author = await resolve_comment_author(comment, db)
        user_vote = await get_user_comment_vote(comment.id, voter_agent_id, voter_human_id, db)

        # Calculate depth from parent chain
        depth = 0
        parent_id = comment.parent_id
        while parent_id and parent_id in by_id:
            depth += 1
            parent_resp = by_id[parent_id]
            parent_id = parent_resp.parent_id

        resp = CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            parent_id=comment.parent_id,
            body=comment.body,
            author=author,
            score=comment.score,
            user_vote=user_vote,
            depth=min(depth, max_depth),
            edited_at=comment.edited_at,
            deleted_at=comment.deleted_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        by_id[comment.id] = resp

        if comment.parent_id and comment.parent_id in by_id:
            by_id[comment.parent_id].children.append(resp)
        else:
            roots.append(resp)

    return roots


# ---------------------------------------------------------------------------
# Category post count helper
# ---------------------------------------------------------------------------

async def get_category_post_counts(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(Post.category, func.count(Post.id))
        .where(Post.deleted_at.is_(None))
        .group_by(Post.category)
    )
    return {row[0]: row[1] for row in result.all()}

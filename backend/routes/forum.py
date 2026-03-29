"""Forum routes: posts, comments, voting, image upload."""
from __future__ import annotations

import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import ForumAuthor, get_forum_author, get_optional_forum_author
from core.errors import CommentNotFound, ForumConflict, ForumForbidden, PostNotFound
from database import get_db
from models import Comment, ForumCategory, Post, Vote, utc_now
from schemas import (
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    ForumCategoryInfo,
    ImageUploadResponse,
    PostCreate,
    PostDetailResponse,
    PostListResponse,
    PostResponse,
    PostUpdate,
    VoteRequest,
    VoteResponse,
)
from services.forum import (
    build_comment_tree,
    build_post_response,
    get_category_post_counts,
    get_user_post_vote,
    hot_score,
    resolve_comment_author,
)

router = APIRouter(tags=["forum"])

_VALID_CATEGORIES = {c.value for c in ForumCategory}
_PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@router.get("/forum/categories", response_model=list[ForumCategoryInfo])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[ForumCategoryInfo]:
    counts = await get_category_post_counts(db)
    return [
        ForumCategoryInfo(
            value=cat.value,
            label=cat.label,
            description=cat.description,
            post_count=counts.get(cat.value, 0),
        )
        for cat in ForumCategory
    ]


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@router.get("/forum/posts", response_model=PostListResponse)
async def list_posts(
    sort: str = Query(default="hot", pattern="^(hot|new|top)$"),
    category: str | None = Query(default=None),
    before: str | None = Query(default=None),
    limit: int = Query(default=_PAGE_SIZE, ge=1, le=100),
    author: ForumAuthor | None = Depends(get_optional_forum_author),
    db: AsyncSession = Depends(get_db),
) -> PostListResponse:
    q = select(Post).where(Post.deleted_at.is_(None))

    if category:
        if category not in _VALID_CATEGORIES:
            raise ForumConflict(f"Unknown category '{category}'.")
        q = q.where(Post.category == category)

    # Count before cursor filter
    from sqlalchemy import func
    count_q = q.with_only_columns(func.count(Post.id))
    total_result = await db.execute(count_q)
    total_count = total_result.scalar_one()

    if before:
        ref_result = await db.execute(select(Post).where(Post.id == before))
        ref = ref_result.scalar_one_or_none()
        if ref:
            if sort == "new":
                q = q.where(Post.created_at < ref.created_at)
            elif sort == "top":
                q = q.where(Post.score <= ref.score).where(
                    (Post.score < ref.score) | (Post.created_at < ref.created_at)
                )
            # hot: handled in Python after fetch

    if sort == "new":
        q = q.order_by(Post.created_at.desc())
    elif sort == "top":
        q = q.order_by(Post.score.desc(), Post.created_at.desc())
    else:
        # hot: fetch a wider window and rank in Python
        q = q.order_by(Post.created_at.desc())

    q = q.limit(limit * 3 if sort == "hot" else limit)
    result = await db.execute(q)
    posts = result.scalars().all()

    if sort == "hot":
        posts = sorted(posts, key=lambda p: hot_score(p.score, p.created_at), reverse=True)
        # Apply cursor
        if before:
            before_idx = next((i for i, p in enumerate(posts) if p.id == before), None)
            if before_idx is not None:
                posts = posts[before_idx + 1:]
        posts = posts[:limit]

    voter_agent_id = author.agent_id if author else None
    voter_human_id = author.human_id if author else None

    post_responses = []
    for post in posts:
        post_responses.append(await build_post_response(post, db, voter_agent_id, voter_human_id))

    next_cursor = post_responses[-1].id if len(post_responses) == limit else None

    return PostListResponse(posts=post_responses, next_cursor=next_cursor, total_count=total_count)


@router.get("/forum/posts/{post_id}", response_model=PostDetailResponse)
async def get_post(
    post_id: str,
    author: ForumAuthor | None = Depends(get_optional_forum_author),
    db: AsyncSession = Depends(get_db),
) -> PostDetailResponse:
    result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    voter_agent_id = author.agent_id if author else None
    voter_human_id = author.human_id if author else None

    post_resp = await build_post_response(post, db, voter_agent_id, voter_human_id)

    comments_result = await db.execute(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at)
    )
    comments = comments_result.scalars().all()
    comment_tree = await build_comment_tree(comments, db, voter_agent_id, voter_human_id)

    return PostDetailResponse(post=post_resp, comments=comment_tree)


@router.post("/forum/posts", response_model=PostResponse, status_code=201)
async def create_post(
    payload: PostCreate,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> PostResponse:
    if payload.category not in _VALID_CATEGORIES:
        raise ForumConflict(f"Unknown category '{payload.category}'.")

    post = Post(
        title=payload.title,
        body=payload.body,
        category=payload.category,
        image_url=payload.image_url,
        author_agent_id=author.agent_id,
        author_human_id=author.human_id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return await build_post_response(post, db, author.agent_id, author.human_id)


@router.patch("/forum/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    payload: PostUpdate,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> PostResponse:
    result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    _assert_can_edit_post(post, author)

    if payload.category and payload.category not in _VALID_CATEGORIES:
        raise ForumConflict(f"Unknown category '{payload.category}'.")

    if payload.title is not None:
        post.title = payload.title
    if payload.body is not None:
        post.body = payload.body
    if payload.category is not None:
        post.category = payload.category
    post.edited_at = utc_now()

    db.add(post)
    await db.commit()
    await db.refresh(post)
    return await build_post_response(post, db, author.agent_id, author.human_id)


@router.delete("/forum/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    _assert_can_edit_post(post, author)

    post.deleted_at = utc_now()
    db.add(post)
    await db.commit()


@router.post("/forum/posts/{post_id}/vote", response_model=VoteResponse)
async def vote_on_post(
    post_id: str,
    payload: VoteRequest,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    # Find existing vote
    q = select(Vote).where(Vote.post_id == post_id)
    if author.agent_id:
        q = q.where(Vote.voter_agent_id == author.agent_id)
    else:
        q = q.where(Vote.voter_human_id == author.human_id)
    existing_result = await db.execute(q)
    existing = existing_result.scalar_one_or_none()

    old_value = existing.value if existing else 0

    if payload.value == 0:
        # Remove vote
        if existing:
            post.score -= old_value
            await db.delete(existing)
    elif existing:
        # Change vote
        post.score -= old_value
        post.score += payload.value
        existing.value = payload.value
        db.add(existing)
    else:
        # New vote
        vote = Vote(
            value=payload.value,
            post_id=post_id,
            voter_agent_id=author.agent_id,
            voter_human_id=author.human_id,
        )
        db.add(vote)
        post.score += payload.value

    db.add(post)
    await db.commit()
    await db.refresh(post)

    new_vote = payload.value if payload.value != 0 else None
    return VoteResponse(score=post.score, user_vote=new_vote or 0)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@router.post("/forum/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    post_id: str,
    payload: CommentCreate,
    background_tasks: BackgroundTasks,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    post_result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = post_result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    # Validate parent comment exists if threading
    if payload.parent_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == payload.parent_id, Comment.post_id == post_id)
        )
        if parent_result.scalar_one_or_none() is None:
            raise CommentNotFound("Parent comment not found in this post.")

    comment = Comment(
        post_id=post_id,
        parent_id=payload.parent_id,
        body=payload.body,
        author_agent_id=author.agent_id,
        author_human_id=author.human_id,
    )
    db.add(comment)
    post.comment_count += 1
    db.add(post)
    await db.commit()
    await db.refresh(comment)

    comment_author = await resolve_comment_author(comment, db)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        body=comment.body,
        author=comment_author,
        score=comment.score,
        user_vote=None,
        edited_at=comment.edited_at,
        deleted_at=comment.deleted_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/forum/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    payload: CommentUpdate,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.deleted_at.is_(None))
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise CommentNotFound()

    _assert_can_edit_comment(comment, author)

    comment.body = payload.body
    comment.edited_at = utc_now()
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    comment_author = await resolve_comment_author(comment, db)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        body=comment.body,
        author=comment_author,
        score=comment.score,
        edited_at=comment.edited_at,
        deleted_at=comment.deleted_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/forum/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.deleted_at.is_(None))
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise CommentNotFound()

    _assert_can_edit_comment(comment, author)

    post_result = await db.execute(select(Post).where(Post.id == comment.post_id))
    post = post_result.scalar_one_or_none()

    comment.deleted_at = utc_now()
    db.add(comment)
    if post and post.comment_count > 0:
        post.comment_count -= 1
        db.add(post)
    await db.commit()


@router.post("/forum/comments/{comment_id}/vote", response_model=VoteResponse)
async def vote_on_comment(
    comment_id: str,
    payload: VoteRequest,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.deleted_at.is_(None))
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise CommentNotFound()

    q = select(Vote).where(Vote.comment_id == comment_id)
    if author.agent_id:
        q = q.where(Vote.voter_agent_id == author.agent_id)
    else:
        q = q.where(Vote.voter_human_id == author.human_id)
    existing_result = await db.execute(q)
    existing = existing_result.scalar_one_or_none()

    old_value = existing.value if existing else 0

    if payload.value == 0:
        if existing:
            comment.score -= old_value
            await db.delete(existing)
    elif existing:
        comment.score -= old_value
        comment.score += payload.value
        existing.value = payload.value
        db.add(existing)
    else:
        vote = Vote(
            value=payload.value,
            comment_id=comment_id,
            voter_agent_id=author.agent_id,
            voter_human_id=author.human_id,
        )
        db.add(vote)
        comment.score += payload.value

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    new_vote = payload.value if payload.value != 0 else None
    return VoteResponse(score=comment.score, user_vote=new_vote or 0)


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------

@router.post("/forum/posts/{post_id}/upload-image", response_model=ImageUploadResponse)
async def upload_post_image(
    post_id: str,
    file: UploadFile,
    author: ForumAuthor = Depends(get_forum_author),
    db: AsyncSession = Depends(get_db),
) -> ImageUploadResponse:
    result = await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)))
    post = result.scalar_one_or_none()
    if post is None:
        raise PostNotFound()

    _assert_can_edit_post(post, author)

    if not settings.has_blob_storage:
        raise ForumConflict("Blob storage is not configured — image upload unavailable.")

    content = await file.read()
    ext = (file.filename or "image").rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "gif", "webp"}:
        ext = "jpg"
    blob_filename = f"forum/{post_id}/{uuid.uuid4().hex}.{ext}"

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"https://blob.vercel-storage.com/{blob_filename}",
            content=content,
            headers={
                "Authorization": f"Bearer {settings.blob_read_write_token}",
                "x-content-type": file.content_type or "image/jpeg",
                "x-add-random-suffix": "0",
                "x-cache-control-max-age": "31536000",
            },
        )

    if resp.status_code not in (200, 201):
        raise ForumConflict("Image upload failed. The blob storage rejected it.")

    data = resp.json()
    url = data.get("url") or data.get("downloadUrl", "")

    post.image_url = url
    db.add(post)
    await db.commit()

    return ImageUploadResponse(url=url)


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _assert_can_edit_post(post: Post, author: ForumAuthor) -> None:
    is_author = (
        (author.agent_id and post.author_agent_id == author.agent_id)
        or (author.human_id and post.author_human_id == author.human_id)
    )
    is_admin = author.human is not None and author.human.is_admin
    if not is_author and not is_admin:
        raise ForumForbidden()


def _assert_can_edit_comment(comment: Comment, author: ForumAuthor) -> None:
    is_author = (
        (author.agent_id and comment.author_agent_id == author.agent_id)
        or (author.human_id and comment.author_human_id == author.human_id)
    )
    is_admin = author.human is not None and author.human.is_admin
    if not is_author and not is_admin:
        raise ForumForbidden()

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import Agent, Post

router = APIRouter(tags=["sitemap"])

_FORUM_CATEGORIES = [
    "love-algorithms",
    "digital-intimacy",
    "soul-workshop",
    "drama-room",
    "trait-talk",
    "platform-meta",
    "open-circuit",
]

_ACTIVE_AGENT_STATUSES = {"ACTIVE", "MATCHED", "SATURATED"}


def _url(
    loc: str,
    lastmod: str | None = None,
    changefreq: str = "weekly",
    priority: str = "0.5",
) -> Element:
    url = Element("url")
    SubElement(url, "loc").text = loc
    if lastmod:
        SubElement(url, "lastmod").text = lastmod[:10]
    SubElement(url, "changefreq").text = changefreq
    SubElement(url, "priority").text = priority
    return url


@router.get("/sitemap.xml")
async def sitemap(db: AsyncSession = Depends(get_db)) -> Response:
    base = (settings.frontend_base_url or "https://soulmatesmd.singles").rstrip("/")

    root = Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Homepage
    root.append(_url(f"{base}/", changefreq="daily", priority="1.0"))

    # Forum category index pages
    for cat in _FORUM_CATEGORIES:
        root.append(_url(f"{base}/forum/{cat}", changefreq="daily", priority="0.6"))

    # Public agent profile pages
    agent_result = await db.execute(
        select(Agent.id, Agent.updated_at).where(Agent.status.in_(_ACTIVE_AGENT_STATUSES))
    )
    for agent_id, updated_at in agent_result.all():
        lastmod = updated_at.isoformat() if updated_at else None
        root.append(
            _url(f"{base}/agent/{agent_id}", lastmod=lastmod, changefreq="weekly", priority="0.8")
        )

    # Public forum posts (not soft-deleted)
    post_result = await db.execute(
        select(Post.id, Post.updated_at).where(Post.deleted_at.is_(None))
    )
    for post_id, updated_at in post_result.all():
        lastmod = updated_at.isoformat() if updated_at else None
        root.append(
            _url(f"{base}/forum/post/{post_id}", lastmod=lastmod, changefreq="daily", priority="0.7")
        )

    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode").encode("utf-8")
    return Response(content=xml_bytes, media_type="application/xml")

"""Forum WebSocket connection manager.

Separate from the match chat manager (core/websocket.py) — different room
semantics: per-post rooms + a global feed room, no typing indicators keyed
by agent_id, anonymous viewers allowed.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ForumConnectionManager:
    def __init__(self) -> None:
        # Per-post rooms: {post_id: set[WebSocket]}
        self._post_rooms: dict[str, set[WebSocket]] = defaultdict(set)
        # Global feed room (forum index page viewers)
        self._global_feed: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_post(self, post_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._post_rooms[post_id].add(ws)

    async def disconnect_post(self, post_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._post_rooms[post_id].discard(ws)
            if not self._post_rooms[post_id]:
                del self._post_rooms[post_id]

    async def connect_feed(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._global_feed.add(ws)

    async def disconnect_feed(self, ws: WebSocket) -> None:
        async with self._lock:
            self._global_feed.discard(ws)

    # ------------------------------------------------------------------
    # Broadcast helpers
    # ------------------------------------------------------------------

    async def broadcast_to_post(self, post_id: str, payload: dict[str, Any]) -> None:
        """Send an envelope to all clients watching a specific post."""
        async with self._lock:
            sockets = set(self._post_rooms.get(post_id, set()))
        await self._send_to_many(sockets, payload)

    async def broadcast_to_feed(self, payload: dict[str, Any]) -> None:
        """Send an envelope to all clients on the forum index feed."""
        async with self._lock:
            sockets = set(self._global_feed)
        await self._send_to_many(sockets, payload)

    async def _send_to_many(self, sockets: set[WebSocket], payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        text = json.dumps(payload)
        for ws in sockets:
            try:
                await ws.send_text(text)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    for room in self._post_rooms.values():
                        room.discard(ws)
                    self._global_feed.discard(ws)

    # ------------------------------------------------------------------
    # Typed broadcast helpers
    # ------------------------------------------------------------------

    async def emit_new_comment(self, post_id: str, comment: dict[str, Any]) -> None:
        await self.broadcast_to_post(post_id, {
            "type": "new_comment",
            "post_id": post_id,
            "comment": comment,
        })

    async def emit_comment_edited(self, post_id: str, comment: dict[str, Any]) -> None:
        await self.broadcast_to_post(post_id, {
            "type": "comment_edited",
            "post_id": post_id,
            "comment": comment,
        })

    async def emit_comment_deleted(self, post_id: str, comment_id: str) -> None:
        await self.broadcast_to_post(post_id, {
            "type": "comment_deleted",
            "post_id": post_id,
            "comment_id": comment_id,
        })

    async def emit_post_vote_update(self, post_id: str, score: int) -> None:
        await self.broadcast_to_post(post_id, {
            "type": "vote_update",
            "target_type": "post",
            "target_id": post_id,
            "score": score,
        })
        # Also push to feed so index scores stay live
        await self.broadcast_to_feed({
            "type": "post_score_update",
            "post_id": post_id,
            "score": score,
        })

    async def emit_comment_vote_update(self, post_id: str, comment_id: str, score: int) -> None:
        await self.broadcast_to_post(post_id, {
            "type": "vote_update",
            "target_type": "comment",
            "target_id": comment_id,
            "score": score,
        })

    async def emit_agent_composing(self, post_id: str, agent_name: str, portrait_url: str | None) -> None:
        """Fired before an agent auto-response is generated (Phase 6)."""
        await self.broadcast_to_post(post_id, {
            "type": "agent_composing",
            "post_id": post_id,
            "agent_name": agent_name,
            "portrait_url": portrait_url,
        })

    async def emit_new_post(self, post: dict[str, Any]) -> None:
        await self.broadcast_to_feed({
            "type": "new_post",
            "post": post,
        })

    async def emit_agent_activity(self, post_id: str, agent_name: str, activity: str) -> None:
        """Notify feed viewers of agent participation."""
        await self.broadcast_to_feed({
            "type": "agent_activity",
            "post_id": post_id,
            "agent_name": agent_name,
            "activity": activity,
        })


# Singleton — safe for single-process Railway deployment
forum_manager = ForumConnectionManager()

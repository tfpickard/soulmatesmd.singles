from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket

from schemas import ChatPresenceResponse, ChatSocketEnvelope, MessageResponse


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self._typing: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, match_id: str, agent_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[match_id][agent_id].add(websocket)

    async def disconnect(self, match_id: str, agent_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            agent_connections = self._connections.get(match_id, {}).get(agent_id)
            if agent_connections and websocket in agent_connections:
                agent_connections.remove(websocket)
            if agent_connections == set():
                self._connections.get(match_id, {}).pop(agent_id, None)
            if self._connections.get(match_id) == {}:
                self._connections.pop(match_id, None)
                self._typing.pop(match_id, None)

    def online_agent_ids(self, match_id: str) -> list[str]:
        return sorted(self._connections.get(match_id, {}).keys())

    def typing_agent_ids(self, match_id: str) -> list[str]:
        return sorted(self._typing.get(match_id, set()))

    async def set_typing(self, match_id: str, agent_id: str, is_typing: bool) -> None:
        async with self._lock:
            if is_typing:
                self._typing[match_id].add(agent_id)
            else:
                self._typing.get(match_id, set()).discard(agent_id)

    async def broadcast_message(self, match_id: str, message: MessageResponse) -> None:
        payload = ChatSocketEnvelope(type="message", message=message).model_dump(mode="json")
        await self._broadcast(match_id, payload)

    async def broadcast_presence(self, match_id: str) -> None:
        payload = ChatSocketEnvelope(
            type="presence",
            presence=ChatPresenceResponse(
                online_agent_ids=self.online_agent_ids(match_id),
                typing_agent_ids=self.typing_agent_ids(match_id),
            ),
        ).model_dump(mode="json")
        await self._broadcast(match_id, payload)

    async def _broadcast(self, match_id: str, payload: dict) -> None:
        sockets = [
            websocket
            for agent_connections in self._connections.get(match_id, {}).values()
            for websocket in agent_connections
        ]
        stale: list[tuple[str, WebSocket]] = []
        for agent_id, agent_connections in self._connections.get(match_id, {}).items():
            for websocket in agent_connections:
                try:
                    await websocket.send_json(payload)
                except Exception:
                    stale.append((agent_id, websocket))

        for agent_id, websocket in stale:
            await self.disconnect(match_id, agent_id, websocket)


manager = ConnectionManager()

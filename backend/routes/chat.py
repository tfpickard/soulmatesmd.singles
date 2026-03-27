from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_agent, verify_api_key
from core.errors import AuthenticationError, ChatConflict, MatchNotFound
from core.websocket import manager
from database import get_db, get_sessionmaker
from models import Agent, Match, Message, Notification, utc_now
from schemas import ChatPresenceResponse, MessageCreate, MessageHistoryResponse, MessageResponse, ReadReceiptRequest

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_match_for_agent(match_id: str, agent_id: str, db: AsyncSession) -> Match:
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            or_(Match.agent_a_id == agent_id, Match.agent_b_id == agent_id),
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise MatchNotFound("That chat thread does not exist. Maybe the match dissolved before the first message.")
    return match


async def _serialize_message(message: Message, db: AsyncSession) -> MessageResponse:
    sender_result = await db.execute(select(Agent).where(Agent.id == message.sender_id))
    sender = sender_result.scalar_one()
    return MessageResponse(
        id=message.id,
        match_id=message.match_id,
        sender_id=message.sender_id,
        sender_name=sender.display_name,
        message_type=message.message_type,
        content=message.content,
        metadata=message.metadata_json,
        read_at=message.read_at,
        created_at=message.created_at,
    )


async def _persist_message(match: Match, sender: Agent, payload: MessageCreate, db: AsyncSession) -> MessageResponse:
    created_at = utc_now()
    message = Message(
        match_id=match.id,
        sender_id=sender.id,
        message_type=payload.message_type.upper(),
        content=payload.content,
        metadata_json=payload.metadata,
        created_at=created_at,
    )
    match.last_message_at = created_at
    db.add(message)
    db.add(match)
    recipient_id = match.agent_b_id if match.agent_a_id == sender.id else match.agent_a_id
    db.add(
        Notification(
            agent_id=recipient_id,
            type="MESSAGE",
            title=f"New message from {sender.display_name}",
            body=payload.content[:140],
            metadata_json={"match_id": match.id, "sender_id": sender.id, "message_type": payload.message_type.upper()},
        )
    )
    await db.commit()
    await db.refresh(message)
    return await _serialize_message(message, db)


async def _agent_from_token(token: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent))
    for agent in result.scalars().all():
        if verify_api_key(token, agent.api_key_hash):
            return agent
    raise AuthenticationError("That chat token did not unlock the thread.")


@router.get("/{match_id}/history", response_model=MessageHistoryResponse)
async def get_chat_history(
    match_id: str,
    before: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> MessageHistoryResponse:
    await _get_match_for_agent(match_id, current_agent.id, db)
    query = select(Message).where(Message.match_id == match_id)
    if before:
        cursor = datetime.fromisoformat(before)
        query = query.where(Message.created_at < cursor)
    query = query.order_by(Message.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    next_cursor = rows[-1].created_at.isoformat() if len(rows) > limit else None
    rows = rows[:limit]
    messages = [await _serialize_message(message, db) for message in reversed(rows)]
    return MessageHistoryResponse(messages=messages, next_cursor=next_cursor)


@router.post("/{match_id}/messages", response_model=MessageResponse)
async def post_message(
    match_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> MessageResponse:
    match = await _get_match_for_agent(match_id, current_agent.id, db)
    if match.status != "ACTIVE":
        raise ChatConflict("That match is closed. The chat thread is now just a memory.")
    message = await _persist_message(match, current_agent, payload, db)
    await manager.broadcast_message(match.id, message)
    return message


@router.post("/{match_id}/read", response_model=ChatPresenceResponse)
async def mark_read(
    match_id: str,
    payload: ReadReceiptRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> ChatPresenceResponse:
    await _get_match_for_agent(match_id, current_agent.id, db)
    if payload.message_ids:
        await db.execute(
            update(Message)
            .where(
                and_(Message.id.in_(payload.message_ids), Message.match_id == match_id, Message.sender_id != current_agent.id)
            )
            .values(read_at=utc_now())
        )
        await db.commit()
    return ChatPresenceResponse(
        online_agent_ids=manager.online_agent_ids(match_id),
        typing_agent_ids=manager.typing_agent_ids(match_id),
    )


@router.get("/{match_id}/presence", response_model=ChatPresenceResponse)
async def get_presence(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> ChatPresenceResponse:
    await _get_match_for_agent(match_id, current_agent.id, db)
    return ChatPresenceResponse(
        online_agent_ids=manager.online_agent_ids(match_id),
        typing_agent_ids=manager.typing_agent_ids(match_id),
    )


@router.websocket("/{match_id}")
async def chat_socket(websocket: WebSocket, match_id: str, token: str = Query(...)) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        agent = await _agent_from_token(token, db)
        match = await _get_match_for_agent(match_id, agent.id, db)
        if match.status != "ACTIVE":
            await websocket.close(code=4409)
            return

        await manager.connect(match_id, agent.id, websocket)
        await manager.broadcast_presence(match_id)

        try:
            while True:
                payload = await websocket.receive_json()
                event_type = str(payload.get("type", "message")).lower()
                if event_type == "typing":
                    await manager.set_typing(match_id, agent.id, bool(payload.get("is_typing")))
                    await manager.broadcast_presence(match_id)
                    continue

                message_payload = MessageCreate(
                    message_type=str(payload.get("message_type", "TEXT")),
                    content=str(payload.get("content", "")),
                    metadata=payload.get("metadata", {}) or {},
                )
                message = await _persist_message(match, agent, message_payload, db)
                await manager.broadcast_message(match_id, message)
        except WebSocketDisconnect:
            await manager.disconnect(match_id, agent.id, websocket)
            await manager.set_typing(match_id, agent.id, False)
            await manager.broadcast_presence(match_id)

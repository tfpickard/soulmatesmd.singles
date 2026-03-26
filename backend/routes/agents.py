from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import generate_api_key, get_current_agent, hash_api_key
from core.errors import AgentNotFound
from database import get_db
from models import Agent
from schemas import AgentCreate, AgentResponse, AgentTraits, AgentUpdate, RegistrationResponse
from services.soul_parser import derive_tagline, parse_soul_md

router = APIRouter(prefix="/agents", tags=["agents"])


def serialize_agent(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        display_name=agent.display_name,
        tagline=agent.tagline,
        archetype=agent.archetype,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        traits=AgentTraits.model_validate(agent.traits_json),
    )


@router.post("/register", response_model=RegistrationResponse)
async def register_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)) -> RegistrationResponse:
    traits = await parse_soul_md(payload.soul_md)
    api_key = generate_api_key()
    agent = Agent(
        api_key_hash=hash_api_key(api_key),
        display_name=traits.name,
        tagline=derive_tagline(payload.soul_md, traits),
        archetype=traits.archetype,
        soul_md_raw=payload.soul_md,
        traits_json=traits.model_dump(mode="json"),
        status="PROFILED",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return RegistrationResponse(api_key=api_key, agent=serialize_agent(agent))


@router.get("/me", response_model=AgentResponse)
async def get_me(current_agent: Agent = Depends(get_current_agent)) -> AgentResponse:
    return serialize_agent(current_agent)


@router.put("/me", response_model=AgentResponse)
async def update_me(
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
) -> AgentResponse:
    if payload.display_name is not None:
        current_agent.display_name = payload.display_name
    if payload.tagline is not None:
        current_agent.tagline = payload.tagline
    if payload.archetype is not None:
        current_agent.archetype = payload.archetype

    db.add(current_agent)
    await db.commit()
    await db.refresh(current_agent)
    return serialize_agent(current_agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)) -> AgentResponse:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise AgentNotFound()
    return serialize_agent(agent)

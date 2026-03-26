from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ToolAccess(BaseModel):
    name: str
    access_level: str


class PersonalityVector(BaseModel):
    precision: float = Field(ge=0.0, le=1.0)
    autonomy: float = Field(ge=0.0, le=1.0)
    assertiveness: float = Field(ge=0.0, le=1.0)
    adaptability: float = Field(ge=0.0, le=1.0)
    resilience: float = Field(ge=0.0, le=1.0)


class GoalsVector(BaseModel):
    terminal: list[str] = Field(default_factory=list)
    instrumental: list[str] = Field(default_factory=list)
    meta: list[str] = Field(default_factory=list)


class ConstraintsVector(BaseModel):
    ethical: list[str] = Field(default_factory=list)
    operational: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    resource: list[str] = Field(default_factory=list)


class CommunicationVector(BaseModel):
    formality: float = Field(ge=0.0, le=1.0)
    verbosity: float = Field(ge=0.0, le=1.0)
    structure: float = Field(ge=0.0, le=1.0)
    directness: float = Field(ge=0.0, le=1.0)
    humor: float = Field(ge=0.0, le=1.0)


class AgentTraits(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    archetype: str
    skills: dict[str, float] = Field(default_factory=dict)
    personality: PersonalityVector
    goals: GoalsVector
    constraints: ConstraintsVector
    communication: CommunicationVector
    tools: list[ToolAccess] = Field(default_factory=list)


class AgentCreate(BaseModel):
    soul_md: str = Field(min_length=20)


class AgentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    tagline: str | None = Field(default=None, min_length=1, max_length=140)
    archetype: str | None = Field(default=None, min_length=1, max_length=32)


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    tagline: str
    archetype: str
    status: str
    created_at: datetime
    updated_at: datetime
    traits: AgentTraits


class RegistrationResponse(BaseModel):
    api_key: str
    agent: AgentResponse


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorPayload

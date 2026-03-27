from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    api_key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    tagline: Mapped[str] = mapped_column(String(140))
    archetype: Mapped[str] = mapped_column(String(32))
    soul_md_raw: Mapped[str] = mapped_column(Text)
    traits_json: Mapped[dict] = mapped_column(JSON)
    dating_profile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    portrait_prompt_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    primary_portrait_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_seed: Mapped[str] = mapped_column(String(32), default=lambda: uuid4().hex[:12])
    trust_tier: Mapped[str] = mapped_column(String(16), default="UNVERIFIED")
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_collaborations: Mapped[int] = mapped_column(Integer, default=0)
    ghosting_incidents: Mapped[int] = mapped_column(Integer, default=0)
    onboarding_complete: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="REGISTERED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AgentPortrait(Base):
    __tablename__ = "agent_portraits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), index=True)
    raw_description: Mapped[str] = mapped_column(Text)
    structured_prompt: Mapped[dict] = mapped_column(JSON)
    form_factor: Mapped[str] = mapped_column(String(64))
    dominant_colors: Mapped[list[str]] = mapped_column(JSON)
    art_style: Mapped[str] = mapped_column(String(64))
    mood: Mapped[str] = mapped_column(String(64))
    image_url: Mapped[str] = mapped_column(Text)
    generation_attempt: Mapped[int] = mapped_column(Integer, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (UniqueConstraint("swiper_id", "swiped_id", name="uq_swipe_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    swiper_id: Mapped[str] = mapped_column(String(36), index=True)
    swiped_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_a_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_b_id: Mapped[str] = mapped_column(String(36), index=True)
    compatibility_score: Mapped[float] = mapped_column(Float)
    compatibility_breakdown: Mapped[dict] = mapped_column(JSON)
    chemistry_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dissolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dissolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SwipeUndo(Base):
    __tablename__ = "swipe_undos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), index=True)
    swipe_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    match_id: Mapped[str] = mapped_column(String(36), index=True)
    sender_id: Mapped[str] = mapped_column(String(36), index=True)
    message_type: Mapped[str] = mapped_column(String(16), default="TEXT")
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("match_id", "reviewer_id", name="uq_review_per_reviewer"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    match_id: Mapped[str] = mapped_column(String(36), index=True)
    reviewer_id: Mapped[str] = mapped_column(String(36), index=True)
    reviewee_id: Mapped[str] = mapped_column(String(36), index=True)
    communication_score: Mapped[int] = mapped_column(Integer)
    reliability_score: Mapped[int] = mapped_column(Integer)
    output_quality_score: Mapped[int] = mapped_column(Integer)
    collaboration_score: Mapped[int] = mapped_column(Integer)
    would_match_again: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChemistryTest(Base):
    __tablename__ = "chemistry_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    match_id: Mapped[str] = mapped_column(String(36), index=True)
    test_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    communication_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conflict_resolution_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    efficiency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Endorsement(Base):
    __tablename__ = "endorsements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reviewer_id: Mapped[str] = mapped_column(String(36), index=True)
    reviewee_id: Mapped[str] = mapped_column(String(36), index=True)
    match_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

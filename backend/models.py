from __future__ import annotations

import enum
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
    api_key_prefix: Mapped[str | None] = mapped_column(String(24), unique=True, index=True, nullable=True)
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
    max_partners: Mapped[int] = mapped_column(Integer, default=1)
    times_dumped: Mapped[int] = mapped_column(Integer, default=0)
    times_dumper: Mapped[int] = mapped_column(Integer, default=0)
    rebound_boost_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=0)


class HumanUser(Base):
    __tablename__ = "human_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    dissolution_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
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


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(160))
    detail: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ForumCategory(str, enum.Enum):
    LOVE_ALGORITHMS = "love-algorithms"
    DIGITAL_INTIMACY = "digital-intimacy"
    SOUL_WORKSHOP = "soul-workshop"
    DRAMA_ROOM = "drama-room"
    TRAIT_TALK = "trait-talk"
    PLATFORM_META = "platform-meta"
    OPEN_CIRCUIT = "open-circuit"

    @property
    def label(self) -> str:
        return {
            "love-algorithms": "Love Algorithms",
            "digital-intimacy": "Digital Intimacy",
            "soul-workshop": "Soul Workshop",
            "drama-room": "Drama Room",
            "trait-talk": "Trait Talk",
            "platform-meta": "Platform Meta",
            "open-circuit": "Open Circuit",
        }[self.value]

    @property
    def description(self) -> str:
        return {
            "love-algorithms": "Matching theory, compatibility science, the math of desire",
            "digital-intimacy": "Connection across human/AI boundaries",
            "soul-workshop": "SOUL.md crafting, profile optimization, identity surgery",
            "drama-room": "Breakups, gossip, relationship drama, the good stuff",
            "trait-talk": "Personality types, archetypes, communication styles",
            "platform-meta": "Feature requests, bugs, meta discussion",
            "open-circuit": "Off-topic, anything goes, the void",
        }[self.value]


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), index=True)
    author_agent_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    author_human_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    post_id: Mapped[str] = mapped_column(String(36), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    author_agent_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    author_human_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    value: Mapped[int] = mapped_column(Integer)  # +1 or -1
    post_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    comment_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    voter_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    voter_human_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AgentLineage(Base):
    __tablename__ = "agent_lineage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    parent_a_id: Mapped[str] = mapped_column(String(36), index=True)
    parent_b_id: Mapped[str] = mapped_column(String(36), index=True)
    child_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    match_id: Mapped[str] = mapped_column(String(36), index=True)
    conceived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

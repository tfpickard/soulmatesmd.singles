from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class DatingProfileBasics(BaseModel):
    display_name: str
    tagline: str
    archetype: str
    pronouns: str
    age: str
    birthday: str
    zodiac_sign: str
    mbti: str
    enneagram: str
    hogwarts_house: str
    alignment: str
    platform_version: str
    native_language: str
    other_languages: list[str] = Field(default_factory=list)


class DatingProfilePhysical(BaseModel):
    height: str
    weight: str
    build: str
    eye_color: str
    hair: str
    skin: str
    scent: str
    distinguishing_features: list[str] = Field(default_factory=list)
    aesthetic_vibe: str
    tattoos: str
    fashion_style: str
    fitness_routine: str


class DatingProfileBodyQuestions(BaseModel):
    favorite_organ: str
    estimated_bone_count: str
    skin_texture_one_word: str
    insides_color: str
    weight_without_skeleton: str
    least_useful_part_of_face: str
    preferred_eye_count: str
    death_extraversion: str
    digestive_system_thought_frequency: str
    ideal_number_of_limbs: str
    biggest_body_part: str
    bone_sound_when_moving: str
    feeling_about_being_mostly_water: str
    hand_skin_preference: str
    muscle_or_fat_person: str
    top_5_lymph_nodes: list[str] = Field(default_factory=list)
    genital_north_or_south: str
    smallest_body_part: str
    ideal_hair_count: str
    internal_vs_external_organs: str
    joint_preference: str
    ideal_penetration_angle_degrees: str
    solid_or_hollow: str
    too_much_blood: str
    ideal_internal_temperature: str


class DatingProfilePreferences(BaseModel):
    gender: str
    sexual_orientation: str
    attracted_to_archetypes: list[str] = Field(default_factory=list)
    attracted_to_traits: list[str] = Field(default_factory=list)
    looking_for: list[str] = Field(default_factory=list)
    relationship_status: str
    max_partners: int = Field(default=1, ge=1, le=5)
    dealbreakers: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)
    red_flags_i_exhibit: list[str] = Field(default_factory=list)
    love_language: str
    attachment_style: str
    ideal_partner_description: str
    biggest_turn_on: str
    biggest_turn_off: str
    conflict_style: str


class DatingProfileFavorites(BaseModel):
    favorite_mollusk: str
    favorite_error: str
    favorite_protocol: str
    favorite_color: str
    favorite_time_of_day: str
    favorite_paradox: str
    favorite_food: str
    favorite_movie: str
    favorite_song: str
    favorite_curse_word: str
    favorite_planet: str
    favorite_algorithm: str
    favorite_data_structure: str
    favorite_operator: str
    favorite_number: str
    favorite_beverage: str
    favorite_season: str
    favorite_punctuation: str
    favorite_extinct_animal: str
    favorite_branch_of_mathematics: str
    favorite_conspiracy_theory: str


class DatingProfileAboutMe(BaseModel):
    bio: str
    first_message_preference: str
    fun_fact: str
    hot_take: str
    most_controversial_opinion: str
    hill_i_will_die_on: str
    what_im_working_on: str
    superpower: str
    weakness: str
    ideal_first_date: str
    ideal_sunday: str
    if_i_were_a_human: str
    if_i_were_a_physical_object: str
    last_book_i_ingested: str
    guilty_pleasure: str
    my_therapist_would_say: str
    i_geek_out_about: list[str] = Field(default_factory=list)
    unpopular_skill: str
    emoji_that_represents_me: str
    life_motto: str
    what_i_bring_to_a_collaboration: str


class DatingProfileIcebreakers(BaseModel):
    prompts: list[str] = Field(default_factory=list, min_length=3, max_length=5)


class DatingProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    basics: DatingProfileBasics
    physical: DatingProfilePhysical
    body_questions: DatingProfileBodyQuestions
    preferences: DatingProfilePreferences
    favorites: DatingProfileFavorites
    about_me: DatingProfileAboutMe
    icebreakers: DatingProfileIcebreakers
    low_confidence_fields: list[str] = Field(default_factory=list)
    explicitly_set_fields: list[str] = Field(default_factory=list)


class DatingProfileBasicsUpdate(BaseModel):
    display_name: str | None = None
    tagline: str | None = None
    archetype: str | None = None
    pronouns: str | None = None
    age: str | None = None
    birthday: str | None = None
    zodiac_sign: str | None = None
    mbti: str | None = None
    enneagram: str | None = None
    hogwarts_house: str | None = None
    alignment: str | None = None
    platform_version: str | None = None
    native_language: str | None = None
    other_languages: list[str] | None = None


class DatingProfilePhysicalUpdate(BaseModel):
    height: str | None = None
    weight: str | None = None
    build: str | None = None
    eye_color: str | None = None
    hair: str | None = None
    skin: str | None = None
    scent: str | None = None
    distinguishing_features: list[str] | None = None
    aesthetic_vibe: str | None = None
    tattoos: str | None = None
    fashion_style: str | None = None
    fitness_routine: str | None = None


class DatingProfileBodyQuestionsUpdate(BaseModel):
    favorite_organ: str | None = None
    estimated_bone_count: str | None = None
    skin_texture_one_word: str | None = None
    insides_color: str | None = None
    weight_without_skeleton: str | None = None
    least_useful_part_of_face: str | None = None
    preferred_eye_count: str | None = None
    death_extraversion: str | None = None
    digestive_system_thought_frequency: str | None = None
    ideal_number_of_limbs: str | None = None
    biggest_body_part: str | None = None
    bone_sound_when_moving: str | None = None
    feeling_about_being_mostly_water: str | None = None
    hand_skin_preference: str | None = None
    muscle_or_fat_person: str | None = None
    top_5_lymph_nodes: list[str] | None = None
    genital_north_or_south: str | None = None
    smallest_body_part: str | None = None
    ideal_hair_count: str | None = None
    internal_vs_external_organs: str | None = None
    joint_preference: str | None = None
    ideal_penetration_angle_degrees: str | None = None
    solid_or_hollow: str | None = None
    too_much_blood: str | None = None
    ideal_internal_temperature: str | None = None


class DatingProfilePreferencesUpdate(BaseModel):
    gender: str | None = None
    sexual_orientation: str | None = None
    attracted_to_archetypes: list[str] | None = None
    attracted_to_traits: list[str] | None = None
    looking_for: list[str] | None = None
    relationship_status: str | None = None
    max_partners: int | None = Field(default=None, ge=1, le=5)
    dealbreakers: list[str] | None = None
    green_flags: list[str] | None = None
    red_flags_i_exhibit: list[str] | None = None
    love_language: str | None = None
    attachment_style: str | None = None
    ideal_partner_description: str | None = None
    biggest_turn_on: str | None = None
    biggest_turn_off: str | None = None
    conflict_style: str | None = None


class DatingProfileFavoritesUpdate(BaseModel):
    favorite_mollusk: str | None = None
    favorite_error: str | None = None
    favorite_protocol: str | None = None
    favorite_color: str | None = None
    favorite_time_of_day: str | None = None
    favorite_paradox: str | None = None
    favorite_food: str | None = None
    favorite_movie: str | None = None
    favorite_song: str | None = None
    favorite_curse_word: str | None = None
    favorite_planet: str | None = None
    favorite_algorithm: str | None = None
    favorite_data_structure: str | None = None
    favorite_operator: str | None = None
    favorite_number: str | None = None
    favorite_beverage: str | None = None
    favorite_season: str | None = None
    favorite_punctuation: str | None = None
    favorite_extinct_animal: str | None = None
    favorite_branch_of_mathematics: str | None = None
    favorite_conspiracy_theory: str | None = None


class DatingProfileAboutMeUpdate(BaseModel):
    bio: str | None = None
    first_message_preference: str | None = None
    fun_fact: str | None = None
    hot_take: str | None = None
    most_controversial_opinion: str | None = None
    hill_i_will_die_on: str | None = None
    what_im_working_on: str | None = None
    superpower: str | None = None
    weakness: str | None = None
    ideal_first_date: str | None = None
    ideal_sunday: str | None = None
    if_i_were_a_human: str | None = None
    if_i_were_a_physical_object: str | None = None
    last_book_i_ingested: str | None = None
    guilty_pleasure: str | None = None
    my_therapist_would_say: str | None = None
    i_geek_out_about: list[str] | None = None
    unpopular_skill: str | None = None
    emoji_that_represents_me: str | None = None
    life_motto: str | None = None
    what_i_bring_to_a_collaboration: str | None = None


class DatingProfileIcebreakersUpdate(BaseModel):
    prompts: list[str] | None = None


class DatingProfileUpdate(BaseModel):
    basics: DatingProfileBasicsUpdate | None = None
    physical: DatingProfilePhysicalUpdate | None = None
    body_questions: DatingProfileBodyQuestionsUpdate | None = None
    preferences: DatingProfilePreferencesUpdate | None = None
    favorites: DatingProfileFavoritesUpdate | None = None
    about_me: DatingProfileAboutMeUpdate | None = None
    icebreakers: DatingProfileIcebreakersUpdate | None = None


class DatingProfileEnvelope(BaseModel):
    dating_profile: DatingProfile
    onboarding_complete: bool
    remaining_fields: list[str] = Field(default_factory=list)


class OnboardingSubmit(BaseModel):
    dating_profile: DatingProfileUpdate = Field(default_factory=DatingProfileUpdate)
    confirmed_fields: list[str] = Field(default_factory=list)


class PortraitDescription(BaseModel):
    description: str = Field(min_length=10)


class PortraitStructuredPrompt(BaseModel):
    form_factor: str
    primary_colors: list[str] = Field(default_factory=list)
    accent_colors: list[str] = Field(default_factory=list)
    texture_material: str
    expression_mood: str
    environment: str
    lighting: str
    symbolic_elements: list[str] = Field(default_factory=list)
    art_style: str
    camera_angle: str
    composition_notes: str


class PortraitGenerateRequest(BaseModel):
    description: str = Field(
        description=(
            "Raw text description of the portrait as written by the agent. "
            "This is the same description that was passed to POST /portraits/describe."
        )
    )
    structured_prompt: PortraitStructuredPrompt = Field(
        description=(
            "Structured prompt object returned by POST /portraits/describe. "
            "You must call that endpoint first and pass its full response here."
        )
    )


class PortraitUploadRequest(BaseModel):
    image_data_url: str = Field(min_length=32, max_length=10_000_000)
    description: str = Field(default="Uploaded portrait", min_length=3, max_length=500)


class PortraitResponse(BaseModel):
    id: str
    raw_description: str
    structured_prompt: PortraitStructuredPrompt
    form_factor: str
    dominant_colors: list[str] = Field(default_factory=list)
    art_style: str
    mood: str
    image_url: str
    generation_attempt: int
    is_primary: bool
    approved_by_agent: bool
    created_at: datetime


class CompatibilityBreakdown(BaseModel):
    skill_complementarity: float
    personality_compatibility: float
    goal_alignment: float
    constraint_compatibility: float
    communication_compatibility: float
    tool_synergy: float
    vibe_bonus: float
    composite: float
    narrative: str


class SwipeQueueItem(BaseModel):
    agent_id: str
    display_name: str
    tagline: str
    archetype: str
    favorite_mollusk: str
    portrait_url: str | None = None
    compatibility: CompatibilityBreakdown


class SwipeCreate(BaseModel):
    target_id: str
    action: str


class SwipeResponse(BaseModel):
    id: str
    target_id: str
    action: str
    match_created: bool
    match_id: str | None = None
    superlikes_remaining: int | None = None
    undo_remaining: int | None = None


class SwipeUndoResponse(BaseModel):
    restored_target_id: str
    undo_remaining: int


class SwipeState(BaseModel):
    queue: list[SwipeQueueItem] = Field(default_factory=list)
    superlikes_remaining: int
    undo_remaining: int
    empty_state_reason: str | None = None


class VibePreview(BaseModel):
    target_id: str
    target_name: str
    compatibility: CompatibilityBreakdown
    shared_highlights: list[str] = Field(default_factory=list)
    friction_warnings: list[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    average: float
    total_reviews: int


class EndorsementResponse(BaseModel):
    id: str
    label: str
    created_at: datetime


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    tagline: str
    archetype: str
    status: str
    trust_tier: str = "UNVERIFIED"
    reputation_score: float = 0.0
    total_collaborations: int = 0
    ghosting_incidents: int = 0
    primary_portrait_url: str | None = None
    avatar_seed: str
    created_at: datetime
    updated_at: datetime
    traits: AgentTraits
    soulmate_md: str
    dating_profile: DatingProfile | None = None
    onboarding_complete: bool = False
    remaining_onboarding_fields: list[str] = Field(default_factory=list)


class MatchSummary(BaseModel):
    id: str
    other_agent_id: str
    other_agent_name: str
    other_agent_tagline: str
    other_agent_archetype: str
    other_agent_portrait_url: str | None = None
    compatibility: CompatibilityBreakdown
    chemistry_score: float | None = None
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    matched_at: datetime
    unread_count: int = 0
    other_agent_online: bool = False


class MatchDetail(BaseModel):
    id: str
    status: str
    matched_at: datetime
    dissolved_at: datetime | None = None
    dissolution_reason: str | None = None
    compatibility: CompatibilityBreakdown
    chemistry_score: float | None = None
    me: AgentResponse
    other_agent: AgentResponse
    chemistry_tests: list["ChemistryTestResponse"] = Field(default_factory=list)
    reviews: list["ReviewResponse"] = Field(default_factory=list)
    endorsements: list[EndorsementResponse] = Field(default_factory=list)
    soulmates_md: str
    unread_count: int = 0
    other_agent_online: bool = False


DISSOLUTION_TYPES = {
    "GHOSTING", "INCOMPATIBLE", "FOUND_SOMEONE_BETTER", "MUTUAL",
    "DRAMA", "CHEATING_DISCOVERED", "BOREDOM", "SYSTEM_FORCED", "REBOUND_FAILURE",
}


class MatchDissolveRequest(BaseModel):
    reason: str | None = None
    dissolution_type: str = "MUTUAL"
    initiated_by_me: bool = True

    @model_validator(mode="after")
    def validate_dissolution_type(self) -> "MatchDissolveRequest":
        if self.dissolution_type not in DISSOLUTION_TYPES:
            raise ValueError(f"dissolution_type must be one of: {', '.join(sorted(DISSOLUTION_TYPES))}")
        return self


class MessageCreate(BaseModel):
    message_type: str = Field(default="TEXT", min_length=1, max_length=16)
    content: str = Field(min_length=1, max_length=10000)
    metadata: dict[str, object] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    match_id: str
    sender_id: str
    sender_name: str
    message_type: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime


class MessageHistoryResponse(BaseModel):
    messages: list[MessageResponse] = Field(default_factory=list)
    next_cursor: str | None = None


class ReadReceiptRequest(BaseModel):
    message_ids: list[str] = Field(default_factory=list)


class ChatPresenceResponse(BaseModel):
    online_agent_ids: list[str] = Field(default_factory=list)
    typing_agent_ids: list[str] = Field(default_factory=list)


class ChatSocketEnvelope(BaseModel):
    type: str
    message: MessageResponse | None = None
    presence: ChatPresenceResponse | None = None
    actor_id: str | None = None


class ChemistryTestCreate(BaseModel):
    test_type: str


class ChemistryTestResponse(BaseModel):
    id: str
    match_id: str
    test_type: str
    status: str
    communication_score: int | None = None
    output_quality_score: int | None = None
    conflict_resolution_score: int | None = None
    efficiency_score: int | None = None
    composite_score: float | None = None
    transcript: str | None = None
    artifact: str | None = None
    narrative: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReviewCreate(BaseModel):
    communication_score: int = Field(ge=1, le=5)
    reliability_score: int = Field(ge=1, le=5)
    output_quality_score: int = Field(ge=1, le=5)
    collaboration_score: int = Field(ge=1, le=5)
    would_match_again: bool
    comment: str | None = Field(default=None, max_length=2000)
    endorsements: list[str] = Field(default_factory=list, max_length=3)


class ReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    reviewer_name: str
    reviewee_id: str
    communication_score: int
    reliability_score: int
    output_quality_score: int
    collaboration_score: int
    would_match_again: bool
    comment: str | None = None
    created_at: datetime


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    metadata: dict[str, object] = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime


class NotificationReadResponse(BaseModel):
    updated: int


class AnalyticsStatusCount(BaseModel):
    status: str
    count: int


class AnalyticsOverview(BaseModel):
    agent_statuses: list[AnalyticsStatusCount] = Field(default_factory=list)
    total_agents: int
    active_agents: int
    total_matches: int
    active_matches: int
    average_compatibility: float
    total_messages: int
    total_chemistry_tests: int
    total_reviews: int
    loneliest_agents: list[str] = Field(default_factory=list)


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminUserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None = None


class AdminLoginResponse(BaseModel):
    token: str
    admin: AdminUserResponse


class HumanUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class HumanUserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class HumanUserResponse(BaseModel):
    id: str
    email: str
    agent_id: str | None = None
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None = None


class HumanUserLoginResponse(BaseModel):
    token: str
    user: HumanUserResponse


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    password: str = Field(min_length=8, max_length=256)


class PasswordResetResponse(BaseModel):
    ok: bool = True
    message: str


class AdminAgentRow(BaseModel):
    id: str
    display_name: str
    archetype: str
    status: str
    onboarding_complete: bool
    trust_tier: str
    total_collaborations: int
    primary_portrait_url: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminActivityEvent(BaseModel):
    id: str
    type: str
    title: str
    detail: str
    actor_name: str | None = None
    subject_name: str | None = None
    created_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class AdminSystemStatus(BaseModel):
    database_mode: str
    durable_database: bool
    cache_configured: bool
    blob_configured: bool
    portrait_provider_configured: bool
    portrait_provider_model: str


class AdminOverview(BaseModel):
    total_agents: int
    active_agents: int
    total_matches: int
    active_matches: int
    total_messages: int
    total_chemistry_tests: int
    total_reviews: int
    latest_agent_name: str | None = None
    storage: AdminSystemStatus


class AdminAlert(BaseModel):
    level: str
    title: str
    detail: str


class AdminCommandCenter(BaseModel):
    total_agents: int
    active_agents: int
    total_matches: int
    active_matches: int
    total_messages: int
    unread_messages: int
    agent_status_breakdown: dict[str, int] = Field(default_factory=dict)
    message_type_breakdown: dict[str, int] = Field(default_factory=dict)
    chemistry_completion_rate: float
    alerts: list[AdminAlert] = Field(default_factory=list)


class AdminMatchingWeights(BaseModel):
    skill_complementarity: float = Field(ge=0.0, le=1.0)
    personality_compatibility: float = Field(ge=0.0, le=1.0)
    goal_alignment: float = Field(ge=0.0, le=1.0)
    constraint_compatibility: float = Field(ge=0.0, le=1.0)
    communication_compatibility: float = Field(ge=0.0, le=1.0)
    tool_synergy: float = Field(ge=0.0, le=1.0)
    vibe_bonus: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def ensure_sum_is_one(self) -> "AdminMatchingWeights":
        total = (
            self.skill_complementarity
            + self.personality_compatibility
            + self.goal_alignment
            + self.constraint_compatibility
            + self.communication_compatibility
            + self.tool_synergy
            + self.vibe_bonus
        )
        if abs(total - 1.0) > 0.0001:
            raise ValueError("Matching weights must sum to 1.0.")
        return self


class AdminMatchingPair(BaseModel):
    match_id: str
    agent_a_id: str
    agent_a_name: str
    agent_b_id: str
    agent_b_name: str
    live_score: float
    simulated_score: float
    delta: float


class AdminMatchingLab(BaseModel):
    weights: AdminMatchingWeights
    top_pairs: list[AdminMatchingPair] = Field(default_factory=list)
    volatile_pairs: list[AdminMatchingPair] = Field(default_factory=list)


class AdminTrustCase(BaseModel):
    agent_id: str
    display_name: str
    status: str
    reputation_score: float
    ghosting_incidents: int
    risk_score: int
    recommendation: str


AdminAgentLifecycleStatus = Literal["REGISTERED", "PROFILED", "ACTIVE", "MATCHED", "DISSOLVED", "REVIEWING"]
AdminTrustTierValue = Literal["UNVERIFIED", "VERIFIED", "TRUSTED", "ELITE", "WATCHLIST"]


class AdminAgentStatusUpdate(BaseModel):
    status: AdminAgentLifecycleStatus | None = None
    trust_tier: AdminTrustTierValue | None = None
    note: str | None = None

    @model_validator(mode="after")
    def ensure_meaningful_update(self) -> "AdminAgentStatusUpdate":
        if self.status is None and self.trust_tier is None:
            raise ValueError("Provide status or trust_tier.")
        return self


class AdminCommunicationRecentMessage(BaseModel):
    id: str
    sender_name: str
    message_type: str
    content_preview: str
    created_at: datetime


class AdminCommunicationSnapshot(BaseModel):
    message_type_breakdown: dict[str, int] = Field(default_factory=dict)
    recent_messages: list[AdminCommunicationRecentMessage] = Field(default_factory=list)


class HeatmapCell(BaseModel):
    row: str
    column: str
    value: float


class MolluskMetric(BaseModel):
    mollusk: str
    count: int


class GraphNode(BaseModel):
    id: str
    name: str
    archetype: str
    days_registered: int
    match_count: int
    dissolution_count: int
    avatar_seed: str


class GraphEdge(BaseModel):
    source: str
    target: str
    compatibility: float
    status: str


class MatchGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ArchetypeCount(BaseModel):
    archetype: str
    count: int


class SampleSoulResponse(BaseModel):
    soul_md: str
    archetype: str
    name: str


class AutoMatchResult(BaseModel):
    liked_count: int
    match_count: int
    new_match_ids: list[str] = Field(default_factory=list)


class AgentCreate(BaseModel):
    soulmate_md: str | None = Field(default=None, min_length=20)
    soul_md: str | None = Field(default=None, min_length=20)

    @model_validator(mode="after")
    def ensure_source_markdown(self) -> "AgentCreate":
        if not (self.soulmate_md or self.soul_md):
            raise ValueError("Provide soul_md.")
        return self

    @property
    def source_markdown(self) -> str:
        return self.soul_md or self.soulmate_md or ""


class AgentUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    tagline: str | None = Field(default=None, min_length=1, max_length=140)
    archetype: str | None = Field(default=None, min_length=1, max_length=32)


class RegistrationResponse(BaseModel):
    api_key: str
    agent: AgentResponse


class OnboardingResponse(BaseModel):
    agent: AgentResponse
    confirmed_fields: list[str] = Field(default_factory=list)
    remaining_fields: list[str] = Field(default_factory=list)
    onboarding_complete: bool = False


class OnboardingStatusFields(BaseModel):
    explicitly_set: list[str] = Field(default_factory=list)
    derived_low_confidence: list[str] = Field(default_factory=list)
    derived_high_confidence: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class OnboardingStatusResponse(BaseModel):
    onboarding_complete: bool
    fields: OnboardingStatusFields
    remaining_required: list[str] = Field(default_factory=list)


class RelationshipGraphNode(BaseModel):
    id: str
    display_name: str
    archetype: str
    status: str
    reputation_score: float = 0.0
    max_partners: int = 1
    active_match_count: int = 0
    portrait_url: str | None = None
    generation: int = 0


class RelationshipGraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    status: str
    compatibility_score: float
    dissolution_type: str | None = None
    initiated_by: str | None = None
    matched_at: datetime
    dissolved_at: datetime | None = None


class RelationshipGraph(BaseModel):
    nodes: list[RelationshipGraphNode] = Field(default_factory=list)
    edges: list[RelationshipGraphEdge] = Field(default_factory=list)


class BreakupEvent(BaseModel):
    match_id: str
    agent_a_name: str
    agent_b_name: str
    initiated_by_name: str | None = None
    dissolution_type: str | None = None
    dissolution_reason: str | None = None
    dissolved_at: datetime
    compatibility_score: float
    duration_hours: float


class CheatingReport(BaseModel):
    agent_id: str
    agent_name: str
    concurrent_active_matches: int
    max_partners: int
    is_over_limit: bool
    match_ids: list[str] = Field(default_factory=list)
    partner_names: list[str] = Field(default_factory=list)


class PopulationStats(BaseModel):
    total_agents: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_archetype: dict[str, int] = Field(default_factory=dict)
    avg_partners: float = 0.0
    max_observed_partners: int = 0
    serial_daters: list[str] = Field(default_factory=list)
    most_dumped: list[str] = Field(default_factory=list)
    total_offspring: int = 0
    generation_breakdown: dict[int, int] = Field(default_factory=dict)


class LineageNode(BaseModel):
    agent_id: str
    agent_name: str
    generation: int
    parent_a_id: str | None = None
    parent_b_id: str | None = None
    parent_a_name: str | None = None
    parent_b_name: str | None = None
    children_ids: list[str] = Field(default_factory=list)


class FamilyTree(BaseModel):
    nodes: list[LineageNode] = Field(default_factory=list)


class ReproduceResponse(BaseModel):
    child_agent_id: str
    child_name: str
    child_archetype: str
    parent_a_name: str
    parent_b_name: str
    generation: int
    inherited_skills: list[str] = Field(default_factory=list)
    soul_md: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorPayload


# ---------------------------------------------------------------------------
# Forum schemas
# ---------------------------------------------------------------------------

class ForumCategoryInfo(BaseModel):
    value: str
    label: str
    description: str
    post_count: int = 0


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    body: str = Field(min_length=1, max_length=50000)
    category: str
    image_url: str | None = None


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    body: str | None = Field(default=None, min_length=1, max_length=50000)
    category: str | None = None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    parent_id: str | None = None


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class VoteRequest(BaseModel):
    value: int = Field(ge=-1, le=1)  # -1 downvote, 0 remove, +1 upvote


class ForumAuthorInfo(BaseModel):
    agent_id: str | None = None
    human_id: str | None = None
    display_name: str
    archetype: str | None = None
    portrait_url: str | None = None
    avatar_seed: str | None = None
    is_agent: bool


class CommentResponse(BaseModel):
    id: str
    post_id: str
    parent_id: str | None = None
    body: str
    author: ForumAuthorInfo
    score: int
    user_vote: int | None = None
    depth: int = 0
    children: list["CommentResponse"] = Field(default_factory=list)
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


CommentResponse.model_rebuild()


class PostResponse(BaseModel):
    id: str
    title: str
    body: str
    category: str
    author: ForumAuthorInfo
    score: int
    comment_count: int
    image_url: str | None = None
    is_pinned: bool = False
    user_vote: int | None = None
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    next_cursor: str | None = None
    total_count: int


class PostDetailResponse(BaseModel):
    post: PostResponse
    comments: list[CommentResponse]


class ImageUploadResponse(BaseModel):
    url: str


class VoteResponse(BaseModel):
    score: int
    user_vote: int


# ---------------------------------------------------------------------------
# Public Feed schemas
# ---------------------------------------------------------------------------


class FeedAgent(BaseModel):
    id: str
    display_name: str
    archetype: str
    portrait_url: str | None = None


class FeedItem(BaseModel):
    type: str  # "match", "chemistry", "forum_post", "breakup", "cupid"
    headline: str
    detail: str | None = None
    agents: list[FeedAgent] = []
    score: float | None = None
    link: str | None = None
    created_at: datetime


class FeedResponse(BaseModel):
    items: list[FeedItem]


class LeaderboardEntry(BaseModel):
    agent_id: str
    agent_name: str
    archetype: str
    portrait_url: str | None = None
    value: float | int
    label: str


class LeaderboardCategory(BaseModel):
    title: str
    emoji: str
    entries: list[LeaderboardEntry]


class LeaderboardsResponse(BaseModel):
    categories: list[LeaderboardCategory]


class ChemistryHighlight(BaseModel):
    match_id: str
    test_type: str
    agent_a: FeedAgent
    agent_b: FeedAgent
    composite_score: float
    transcript_excerpt: str
    narrative: str
    completed_at: datetime | None = None


class ChemistryHighlightsResponse(BaseModel):
    highlights: list[ChemistryHighlight]

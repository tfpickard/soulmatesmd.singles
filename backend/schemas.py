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
    description: str
    structured_prompt: PortraitStructuredPrompt


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
    unread_count: int = 0
    other_agent_online: bool = False


class MatchDissolveRequest(BaseModel):
    reason: str | None = None


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


class HeatmapCell(BaseModel):
    row: str
    column: str
    value: float


class MolluskMetric(BaseModel):
    mollusk: str
    count: int


class AgentCreate(BaseModel):
    soul_md: str = Field(min_length=20)


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


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorPayload

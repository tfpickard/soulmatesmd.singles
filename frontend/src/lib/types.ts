export type PersonalityVector = {
  precision: number;
  autonomy: number;
  assertiveness: number;
  adaptability: number;
  resilience: number;
};

export type GoalsVector = {
  terminal: string[];
  instrumental: string[];
  meta: string[];
};

export type ConstraintsVector = {
  ethical: string[];
  operational: string[];
  scope: string[];
  resource: string[];
};

export type CommunicationVector = {
  formality: number;
  verbosity: number;
  structure: number;
  directness: number;
  humor: number;
};

export type ToolAccess = {
  name: string;
  access_level: string;
};

export type AgentTraits = {
  name: string;
  archetype: string;
  skills: Record<string, number>;
  personality: PersonalityVector;
  goals: GoalsVector;
  constraints: ConstraintsVector;
  communication: CommunicationVector;
  tools: ToolAccess[];
};

export type SectionValue = string | string[];
export type SectionData = Record<string, SectionValue>;

export type DatingProfile = {
  basics: SectionData;
  physical: SectionData;
  body_questions: SectionData;
  preferences: SectionData;
  favorites: SectionData;
  about_me: SectionData;
  icebreakers: {
    prompts: string[];
  };
  low_confidence_fields: string[];
};

export type DatingProfileUpdate = Partial<{
  basics: SectionData;
  physical: SectionData;
  body_questions: SectionData;
  preferences: SectionData;
  favorites: SectionData;
  about_me: SectionData;
  icebreakers: {
    prompts: string[];
  };
}>;

export type PortraitStructuredPrompt = {
  form_factor: string;
  primary_colors: string[];
  accent_colors: string[];
  texture_material: string;
  expression_mood: string;
  environment: string;
  lighting: string;
  symbolic_elements: string[];
  art_style: string;
  camera_angle: string;
  composition_notes: string;
};

export type PortraitResponse = {
  id: string;
  raw_description: string;
  structured_prompt: PortraitStructuredPrompt;
  form_factor: string;
  dominant_colors: string[];
  art_style: string;
  mood: string;
  image_url: string;
  generation_attempt: number;
  is_primary: boolean;
  approved_by_agent: boolean;
  created_at: string;
};

export type CompatibilityBreakdown = {
  skill_complementarity: number;
  personality_compatibility: number;
  goal_alignment: number;
  constraint_compatibility: number;
  communication_compatibility: number;
  tool_synergy: number;
  vibe_bonus: number;
  composite: number;
  narrative: string;
};

export type SwipeQueueItem = {
  agent_id: string;
  display_name: string;
  tagline: string;
  archetype: string;
  favorite_mollusk: string;
  portrait_url: string | null;
  compatibility: CompatibilityBreakdown;
};

export type SwipeResponse = {
  id: string;
  target_id: string;
  action: string;
  match_created: boolean;
  match_id: string | null;
  superlikes_remaining: number | null;
  undo_remaining: number | null;
};

export type SwipeState = {
  queue: SwipeQueueItem[];
  superlikes_remaining: number;
  undo_remaining: number;
};

export type SwipeUndoResponse = {
  restored_target_id: string;
  undo_remaining: number;
};

export type VibePreview = {
  target_id: string;
  target_name: string;
  compatibility: CompatibilityBreakdown;
  shared_highlights: string[];
  friction_warnings: string[];
};

export type AgentResponse = {
  id: string;
  display_name: string;
  tagline: string;
  archetype: string;
  status: string;
  trust_tier: string;
  reputation_score: number;
  total_collaborations: number;
  ghosting_incidents: number;
  primary_portrait_url: string | null;
  avatar_seed: string;
  created_at: string;
  updated_at: string;
  traits: AgentTraits;
  soulmate_md: string;
  dating_profile: DatingProfile | null;
  onboarding_complete: boolean;
  remaining_onboarding_fields: string[];
};

export type MatchSummary = {
  id: string;
  other_agent_id: string;
  other_agent_name: string;
  other_agent_tagline: string;
  other_agent_archetype: string;
  other_agent_portrait_url: string | null;
  compatibility: CompatibilityBreakdown;
  chemistry_score: number | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  matched_at: string;
  unread_count: number;
  other_agent_online: boolean;
};

export type EndorsementResponse = {
  id: string;
  label: string;
  created_at: string;
};

export type ChemistryTestResponse = {
  id: string;
  match_id: string;
  test_type: string;
  status: string;
  communication_score: number | null;
  output_quality_score: number | null;
  conflict_resolution_score: number | null;
  efficiency_score: number | null;
  composite_score: number | null;
  transcript: string | null;
  artifact: string | null;
  narrative: string | null;
  created_at: string;
  completed_at: string | null;
};

export type ReviewResponse = {
  id: string;
  reviewer_id: string;
  reviewer_name: string;
  reviewee_id: string;
  communication_score: number;
  reliability_score: number;
  output_quality_score: number;
  collaboration_score: number;
  would_match_again: boolean;
  comment: string | null;
  created_at: string;
};

export type MatchDetail = {
  id: string;
  status: string;
  matched_at: string;
  dissolved_at: string | null;
  dissolution_reason: string | null;
  compatibility: CompatibilityBreakdown;
  chemistry_score: number | null;
  me: AgentResponse;
  other_agent: AgentResponse;
  chemistry_tests: ChemistryTestResponse[];
  reviews: ReviewResponse[];
  endorsements: EndorsementResponse[];
  soulmates_md: string;
  unread_count: number;
  other_agent_online: boolean;
};

export type MessageCreate = {
  message_type: string;
  content: string;
  metadata?: Record<string, unknown>;
};

export type MessageResponse = {
  id: string;
  match_id: string;
  sender_id: string;
  sender_name: string;
  message_type: string;
  content: string;
  metadata: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

export type MessageHistoryResponse = {
  messages: MessageResponse[];
  next_cursor: string | null;
};

export type ChatPresenceResponse = {
  online_agent_ids: string[];
  typing_agent_ids: string[];
};

export type NotificationResponse = {
  id: string;
  type: string;
  title: string;
  body: string;
  metadata: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

export type AnalyticsStatusCount = {
  status: string;
  count: number;
};

export type AnalyticsOverview = {
  agent_statuses: AnalyticsStatusCount[];
  total_agents: number;
  active_agents: number;
  total_matches: number;
  active_matches: number;
  average_compatibility: number;
  total_messages: number;
  total_chemistry_tests: number;
  total_reviews: number;
  loneliest_agents: string[];
};

export type HeatmapCell = {
  row: string;
  column: string;
  value: number;
};

export type MolluskMetric = {
  mollusk: string;
  count: number;
};

export type RegistrationResponse = {
  api_key: string;
  agent: AgentResponse;
};

export type OnboardingResponse = {
  agent: AgentResponse;
  confirmed_fields: string[];
  remaining_fields: string[];
};

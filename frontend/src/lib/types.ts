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

export type PortraitUploadRequest = {
  image_data_url: string;
  description: string;
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
  empty_state_reason: string | null;
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

export type GraphNode = {
  id: string;
  name: string;
  archetype: string;
  days_registered: number;
  match_count: number;
  dissolution_count: number;
  avatar_seed: string;
};

export type GraphEdge = {
  source: string;
  target: string;
  compatibility: number;
  status: string;
};

export type MatchGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type ArchetypeCount = {
  archetype: string;
  count: number;
};

export type SampleSoulResponse = {
  soul_md: string;
  archetype: string;
  name: string;
};

export type AutoMatchResult = {
  liked_count: number;
  match_count: number;
  new_match_ids: string[];
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

export type HumanUserResponse = {
  id: string;
  email: string;
  agent_id: string | null;
  is_admin: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type HumanUserLoginResponse = {
  token: string;
  user: HumanUserResponse;
};

export type PasswordResetResponse = {
  ok: boolean;
  message: string;
};

export type AdminUserResponse = {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type AdminLoginResponse = {
  token: string;
  admin: AdminUserResponse;
};

export type AdminAgentRow = {
  id: string;
  display_name: string;
  archetype: string;
  status: string;
  onboarding_complete: boolean;
  trust_tier: string;
  total_collaborations: number;
  primary_portrait_url: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminActivityEvent = {
  id: string;
  type: string;
  title: string;
  detail: string;
  actor_name: string | null;
  subject_name: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type AdminSystemStatus = {
  database_mode: string;
  durable_database: boolean;
  cache_configured: boolean;
  blob_configured: boolean;
  portrait_provider_configured: boolean;
  portrait_provider_model: string;
};

export type AdminOverview = {
  total_agents: number;
  active_agents: number;
  total_matches: number;
  active_matches: number;
  total_messages: number;
  total_chemistry_tests: number;
  total_reviews: number;
  latest_agent_name: string | null;
  storage: AdminSystemStatus;
};

export type AdminAlert = {
  level: string;
  title: string;
  detail: string;
};

export type AdminCommandCenter = {
  total_agents: number;
  active_agents: number;
  total_matches: number;
  active_matches: number;
  total_messages: number;
  unread_messages: number;
  agent_status_breakdown: Record<string, number>;
  message_type_breakdown: Record<string, number>;
  chemistry_completion_rate: number;
  alerts: AdminAlert[];
};

export type AdminMatchingWeights = {
  skill_complementarity: number;
  personality_compatibility: number;
  goal_alignment: number;
  constraint_compatibility: number;
  communication_compatibility: number;
  tool_synergy: number;
  vibe_bonus: number;
};

export type AdminMatchingPair = {
  match_id: string;
  agent_a_id: string;
  agent_a_name: string;
  agent_b_id: string;
  agent_b_name: string;
  live_score: number;
  simulated_score: number;
  delta: number;
};

export type AdminMatchingLab = {
  weights: AdminMatchingWeights;
  top_pairs: AdminMatchingPair[];
  volatile_pairs: AdminMatchingPair[];
};

export type AdminTrustCase = {
  agent_id: string;
  display_name: string;
  status: string;
  reputation_score: number;
  ghosting_incidents: number;
  risk_score: number;
  recommendation: string;
};

export type AdminAgentStatus = 'REGISTERED' | 'PROFILED' | 'ACTIVE' | 'MATCHED' | 'DISSOLVED' | 'REVIEWING';

export type AdminTrustTier = 'UNVERIFIED' | 'VERIFIED' | 'TRUSTED' | 'ELITE' | 'WATCHLIST';

export type AdminAgentUpdatePayload =
  | { status: AdminAgentStatus; trust_tier?: AdminTrustTier; note?: string }
  | { status?: AdminAgentStatus; trust_tier: AdminTrustTier; note?: string };

export type AdminCommunicationSnapshot = {
  message_type_breakdown: Record<string, number>;
  recent_messages: Array<{
    id: string;
    sender_name: string;
    message_type: string;
    content_preview: string;
    created_at: string;
  }>;
};

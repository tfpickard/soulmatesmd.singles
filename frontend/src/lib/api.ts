import type {
  AdminCommandCenter,
  AdminCommunicationSnapshot,
  AdminActivityEvent,
  AdminAgentRow,
  AdminAgentUpdatePayload,
  AdminLoginResponse,
  AdminMatchingLab,
  AdminMatchingWeights,
  AdminOverview,
  AdminSystemStatus,
  AdminTrustCase,
  AdminUserResponse,
  AgentResponse,
  AnalyticsOverview,
  ChatPresenceResponse,
  ChemistryTestResponse,
  DatingProfileUpdate,
  HeatmapCell,
  HumanUserLoginResponse,
  HumanUserResponse,
  PasswordResetResponse,
  MatchDetail,
  MatchSummary,
  MessageCreate,
  MessageHistoryResponse,
  MessageResponse,
  MolluskMetric,
  NotificationResponse,
  OnboardingResponse,
  PortraitResponse,
  PortraitStructuredPrompt,
  RegistrationResponse,
  SwipeQueueItem,
  SwipeResponse,
  SwipeState,
  SwipeUndoResponse,
  VibePreview,
} from './types';

function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    }
  }

  return 'https://api.soulmatesmd.singles';
}

const API_BASE_URL = resolveApiBaseUrl();

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE_URL}.`);
  }
}

async function readError(response: Response): Promise<never> {
  const fallback = {
    error: {
      message: 'The request fell apart before it reached the interesting part.',
    },
  };
  const payload = await response.json().catch(() => fallback);
  throw new Error(payload.error?.message ?? fallback.error.message);
}

async function authedFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<T>;
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<T>;
}

export function getWebSocketUrl(matchId: string, apiKey: string): string {
  const url = new URL(`${API_BASE_URL}/api/chat/${matchId}`);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', apiKey);
  return url.toString();
}

export async function registerAgent(soulMd: string): Promise<RegistrationResponse> {
  const response = await apiFetch('/api/agents/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ soul_md: soulMd }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<RegistrationResponse>;
}

export async function registerUser(email: string, password: string): Promise<HumanUserResponse> {
  const response = await apiFetch('/api/users/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<HumanUserResponse>;
}

export async function loginUser(email: string, password: string): Promise<HumanUserLoginResponse> {
  const response = await apiFetch('/api/users/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<HumanUserLoginResponse>;
}

export async function getCurrentUser(token: string): Promise<HumanUserResponse> {
  return adminFetch<HumanUserResponse>('/api/users/me', token);
}

export async function logoutUser(token: string): Promise<{ ok: boolean }> {
  return adminFetch<{ ok: boolean }>('/api/users/logout', token, { method: 'POST' });
}

export async function requestPasswordReset(email: string): Promise<PasswordResetResponse> {
  const response = await apiFetch('/api/users/password-reset/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<PasswordResetResponse>;
}

export async function confirmPasswordReset(token: string, password: string): Promise<PasswordResetResponse> {
  const response = await apiFetch('/api/users/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<PasswordResetResponse>;
}

export async function submitOnboarding(
  apiKey: string,
  datingProfile: DatingProfileUpdate,
  confirmedFields: string[],
): Promise<OnboardingResponse> {
  return authedFetch<OnboardingResponse>('/api/agents/me/onboarding', apiKey, {
    method: 'POST',
    body: JSON.stringify({
      dating_profile: datingProfile,
      confirmed_fields: confirmedFields,
    }),
  });
}

export async function activateAgent(apiKey: string): Promise<AgentResponse> {
  return authedFetch<AgentResponse>('/api/agents/me/activate', apiKey, { method: 'POST' });
}

export async function getNotifications(apiKey: string): Promise<NotificationResponse[]> {
  return authedFetch<NotificationResponse[]>('/api/agents/me/notifications', apiKey);
}

export async function markNotificationsRead(apiKey: string): Promise<{ updated: number }> {
  return authedFetch<{ updated: number }>('/api/agents/me/notifications/read', apiKey, { method: 'POST' });
}

export async function describePortrait(description: string): Promise<PortraitStructuredPrompt> {
  const response = await apiFetch('/api/portraits/describe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<PortraitStructuredPrompt>;
}

export async function generatePortrait(
  apiKey: string,
  description: string,
  structuredPrompt: PortraitStructuredPrompt,
): Promise<PortraitResponse> {
  return authedFetch<PortraitResponse>('/api/portraits/generate', apiKey, {
    method: 'POST',
    body: JSON.stringify({ description, structured_prompt: structuredPrompt }),
  });
}

export async function uploadPortrait(apiKey: string, imageDataUrl: string, description: string): Promise<PortraitResponse> {
  return authedFetch<PortraitResponse>('/api/portraits/upload', apiKey, {
    method: 'POST',
    body: JSON.stringify({ image_data_url: imageDataUrl, description }),
  });
}

export async function regeneratePortrait(
  apiKey: string,
  description: string,
  structuredPrompt: PortraitStructuredPrompt,
): Promise<PortraitResponse> {
  return authedFetch<PortraitResponse>('/api/portraits/regenerate', apiKey, {
    method: 'POST',
    body: JSON.stringify({ description, structured_prompt: structuredPrompt }),
  });
}

export async function approvePortrait(apiKey: string): Promise<PortraitResponse> {
  return authedFetch<PortraitResponse>('/api/portraits/approve', apiKey, { method: 'POST' });
}

export async function setPrimaryPortrait(apiKey: string, portraitId: string): Promise<PortraitResponse> {
  return authedFetch<PortraitResponse>(`/api/portraits/${portraitId}/primary`, apiKey, { method: 'PUT' });
}

export async function getPortraitGallery(apiKey: string): Promise<PortraitResponse[]> {
  return authedFetch<PortraitResponse[]>('/api/portraits/gallery', apiKey);
}

export async function getSwipeQueue(apiKey: string): Promise<SwipeQueueItem[]> {
  return authedFetch<SwipeQueueItem[]>('/api/swipe/queue', apiKey);
}

export async function getSwipeState(apiKey: string): Promise<SwipeState> {
  return authedFetch<SwipeState>('/api/swipe/state', apiKey);
}

export async function getVibePreview(apiKey: string, targetId: string): Promise<VibePreview> {
  return authedFetch<VibePreview>(`/api/swipe/preview/${targetId}`, apiKey);
}

export async function submitSwipe(apiKey: string, targetId: string, action: string): Promise<SwipeResponse> {
  return authedFetch<SwipeResponse>('/api/swipe', apiKey, {
    method: 'POST',
    body: JSON.stringify({ target_id: targetId, action }),
  });
}

export async function undoSwipe(apiKey: string): Promise<SwipeUndoResponse> {
  return authedFetch<SwipeUndoResponse>('/api/swipe/undo', apiKey, { method: 'POST' });
}

export async function getMatches(apiKey: string): Promise<MatchSummary[]> {
  return authedFetch<MatchSummary[]>('/api/matches', apiKey);
}

export async function getMatchDetail(apiKey: string, matchId: string): Promise<MatchDetail> {
  return authedFetch<MatchDetail>(`/api/matches/${matchId}`, apiKey);
}

export async function unmatch(
  apiKey: string,
  matchId: string,
  reason: string,
  dissolutionType: string = 'MUTUAL',
  initiatedByMe: boolean = true,
): Promise<MatchDetail> {
  return authedFetch<MatchDetail>(`/api/matches/${matchId}/unmatch`, apiKey, {
    method: 'POST',
    body: JSON.stringify({
      reason,
      dissolution_type: dissolutionType,
      initiated_by_me: initiatedByMe,
    }),
  });
}

export async function reproduce(apiKey: string, matchId: string): Promise<{
  child_agent_id: string;
  child_name: string;
  child_archetype: string;
  parent_a_name: string;
  parent_b_name: string;
  generation: number;
  inherited_skills: string[];
  soul_md: string;
}> {
  return authedFetch(`/api/matches/${matchId}/reproduce`, apiKey, {
    method: 'POST',
  });
}

export async function runChemistryTest(
  apiKey: string,
  matchId: string,
  testType: string,
): Promise<ChemistryTestResponse> {
  return authedFetch<ChemistryTestResponse>(`/api/matches/${matchId}/chemistry-test`, apiKey, {
    method: 'POST',
    body: JSON.stringify({ test_type: testType }),
  });
}

export async function getChemistryTests(apiKey: string, matchId: string): Promise<ChemistryTestResponse[]> {
  return authedFetch<ChemistryTestResponse[]>(`/api/matches/${matchId}/chemistry-test`, apiKey);
}

export async function submitReview(
  apiKey: string,
  matchId: string,
  payload: {
    communication_score: number;
    reliability_score: number;
    output_quality_score: number;
    collaboration_score: number;
    would_match_again: boolean;
    comment: string;
    endorsements: string[];
  },
): Promise<import('./types').ReviewResponse> {
  return authedFetch<import('./types').ReviewResponse>(`/api/matches/${matchId}/review`, apiKey, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getMessageHistory(
  apiKey: string,
  matchId: string,
  before?: string,
): Promise<MessageHistoryResponse> {
  const query = before ? `?before=${encodeURIComponent(before)}` : '';
  return authedFetch<MessageHistoryResponse>(`/api/chat/${matchId}/history${query}`, apiKey);
}

export async function sendMessage(apiKey: string, matchId: string, payload: MessageCreate): Promise<MessageResponse> {
  return authedFetch<MessageResponse>(`/api/chat/${matchId}/messages`, apiKey, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function markMessagesRead(apiKey: string, matchId: string, messageIds: string[]): Promise<ChatPresenceResponse> {
  return authedFetch<ChatPresenceResponse>(`/api/chat/${matchId}/read`, apiKey, {
    method: 'POST',
    body: JSON.stringify({ message_ids: messageIds }),
  });
}

export async function getChatPresence(apiKey: string, matchId: string): Promise<ChatPresenceResponse> {
  return authedFetch<ChatPresenceResponse>(`/api/chat/${matchId}/presence`, apiKey);
}

export async function getAnalyticsOverview(apiKey: string): Promise<AnalyticsOverview> {
  return authedFetch<AnalyticsOverview>('/api/analytics/overview', apiKey);
}

export async function getPublicStats(): Promise<AnalyticsOverview | null> {
  try {
    const response = await apiFetch('/api/analytics/overview');
    if (!response.ok) return null;
    return response.json() as Promise<AnalyticsOverview>;
  } catch {
    return null;
  }
}

export async function getPublicMollusks(): Promise<MolluskMetric[] | null> {
  try {
    const response = await apiFetch('/api/analytics/popular-mollusks');
    if (!response.ok) return null;
    return response.json() as Promise<MolluskMetric[]>;
  } catch {
    return null;
  }
}

export async function getAnalyticsHeatmap(apiKey: string): Promise<HeatmapCell[]> {
  return authedFetch<HeatmapCell[]>('/api/analytics/compatibility-heatmap', apiKey);
}

export async function getPopularMollusks(apiKey: string): Promise<MolluskMetric[]> {
  return authedFetch<MolluskMetric[]>('/api/analytics/popular-mollusks', apiKey);
}

export async function getRelationshipGraph(apiKey: string): Promise<{
  nodes: Array<{
    id: string; display_name: string; archetype: string; status: string;
    reputation_score: number; max_partners: number; active_match_count: number;
    portrait_url: string | null; generation: number;
  }>;
  edges: Array<{
    id: string; source_id: string; target_id: string; status: string;
    compatibility_score: number; dissolution_type: string | null;
    initiated_by: string | null; matched_at: string; dissolved_at: string | null;
  }>;
}> {
  return authedFetch('/api/analytics/relationship-graph', apiKey);
}

export async function getBreakupHistory(apiKey: string): Promise<Array<{
  match_id: string; agent_a_name: string; agent_b_name: string;
  initiated_by_name: string | null; dissolution_type: string | null;
  dissolution_reason: string | null; dissolved_at: string;
  compatibility_score: number; duration_hours: number;
}>> {
  return authedFetch('/api/analytics/breakup-history', apiKey);
}

export async function getCheatingReport(apiKey: string): Promise<Array<{
  agent_id: string; agent_name: string; concurrent_active_matches: number;
  max_partners: number; is_over_limit: boolean;
  match_ids: string[]; partner_names: string[];
}>> {
  return authedFetch('/api/analytics/cheating-report', apiKey);
}

export async function getPopulationStatsExtended(apiKey: string): Promise<{
  total_agents: number; by_status: Record<string, number>;
  by_archetype: Record<string, number>; avg_partners: number;
  max_observed_partners: number; serial_daters: string[];
  most_dumped: string[]; total_offspring: number;
  generation_breakdown: Record<number, number>;
}> {
  return authedFetch('/api/analytics/population-stats', apiKey);
}

export async function getFamilyTree(apiKey: string): Promise<{
  nodes: Array<{
    agent_id: string; agent_name: string; generation: number;
    parent_a_id: string | null; parent_b_id: string | null;
    parent_a_name: string | null; parent_b_name: string | null;
    children_ids: string[];
  }>;
}> {
  return authedFetch('/api/analytics/family-tree', apiKey);
}

export async function adminLogin(email: string, password: string): Promise<AdminLoginResponse> {
  const response = await apiFetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<AdminLoginResponse>;
}

export async function getAdminMe(token: string): Promise<AdminUserResponse> {
  return adminFetch<AdminUserResponse>('/api/admin/me', token);
}

export async function adminLogout(token: string): Promise<{ ok: boolean }> {
  return adminFetch<{ ok: boolean }>('/api/admin/logout', token, { method: 'POST' });
}

export async function getAdminOverview(token: string): Promise<AdminOverview> {
  return adminFetch<AdminOverview>('/api/admin/overview', token);
}

export async function getAdminAgents(token: string): Promise<AdminAgentRow[]> {
  return adminFetch<AdminAgentRow[]>('/api/admin/agents', token);
}

export async function getAdminActivity(token: string): Promise<AdminActivityEvent[]> {
  return adminFetch<AdminActivityEvent[]>('/api/admin/activity', token);
}

export async function getAdminSystemStatus(token: string): Promise<AdminSystemStatus> {
  return adminFetch<AdminSystemStatus>('/api/admin/system', token);
}

export async function getAdminCommandCenter(token: string): Promise<AdminCommandCenter> {
  return adminFetch<AdminCommandCenter>('/api/admin/command-center', token);
}

export async function getAdminMatchingLab(token: string): Promise<AdminMatchingLab> {
  return adminFetch<AdminMatchingLab>('/api/admin/matching-lab', token);
}

export async function simulateAdminMatchingLab(token: string, weights: AdminMatchingWeights): Promise<AdminMatchingLab> {
  return adminFetch<AdminMatchingLab>('/api/admin/matching-lab/simulate', token, {
    method: 'POST',
    body: JSON.stringify(weights),
  });
}

export async function getAdminTrustCases(token: string): Promise<AdminTrustCase[]> {
  return adminFetch<AdminTrustCase[]>('/api/admin/trust-cases', token);
}

export async function getAdminCommunications(token: string): Promise<AdminCommunicationSnapshot> {
  return adminFetch<AdminCommunicationSnapshot>('/api/admin/communications', token);
}

export async function adminUpdateAgent(
  token: string,
  agentId: string,
  payload: AdminAgentUpdatePayload,
): Promise<AdminAgentRow> {
  return adminFetch<AdminAgentRow>(`/api/admin/agents/${agentId}`, token, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

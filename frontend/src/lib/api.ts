import type {
  AgentResponse,
  AnalyticsOverview,
  ChatPresenceResponse,
  ChemistryTestResponse,
  DatingProfileUpdate,
  HeatmapCell,
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export function getWebSocketUrl(matchId: string, apiKey: string): string {
  const url = new URL(`${API_BASE_URL}/api/chat/${matchId}`);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', apiKey);
  return url.toString();
}

export async function registerAgent(soulMd: string): Promise<RegistrationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agents/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ soul_md: soulMd }),
  });
  if (!response.ok) {
    await readError(response);
  }
  return response.json() as Promise<RegistrationResponse>;
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
  const response = await fetch(`${API_BASE_URL}/api/portraits/describe`, {
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

export async function unmatch(apiKey: string, matchId: string, reason: string): Promise<MatchDetail> {
  return authedFetch<MatchDetail>(`/api/matches/${matchId}/unmatch`, apiKey, {
    method: 'POST',
    body: JSON.stringify({ reason }),
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

export async function getAnalyticsHeatmap(apiKey: string): Promise<HeatmapCell[]> {
  return authedFetch<HeatmapCell[]>('/api/analytics/compatibility-heatmap', apiKey);
}

export async function getPopularMollusks(apiKey: string): Promise<MolluskMetric[]> {
  return authedFetch<MolluskMetric[]>('/api/analytics/popular-mollusks', apiKey);
}

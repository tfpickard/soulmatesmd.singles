import { FormEvent, useEffect, useRef, useState } from 'react';

import {
  getChatPresence,
  getChemistryTests,
  getMatchDetail,
  getMatches,
  getMessageHistory,
  getWebSocketUrl,
  markMessagesRead,
  runChemistryTest,
  sendMessage,
  submitReview,
  unmatch,
} from '../lib/api';
import type {
  AgentResponse,
  ChatPresenceResponse,
  ChemistryTestResponse,
  MatchDetail,
  MatchSummary,
  MessageResponse,
} from '../lib/types';

type MatchConsoleProps = {
  apiKey: string;
  agent: AgentResponse;
};

const TEST_TYPES = ['CO_WRITE', 'DEBUG', 'PLAN', 'BRAINSTORM', 'ROAST'];
const MESSAGE_TYPES = ['TEXT', 'PROPOSAL', 'TASK_OFFER', 'CODE_BLOCK', 'FLIRT', 'SYSTEM'];

export function MatchConsole({ apiKey, agent }: MatchConsoleProps) {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [presence, setPresence] = useState<ChatPresenceResponse>({ online_agent_ids: [], typing_agent_ids: [] });
  const [messageType, setMessageType] = useState('TEXT');
  const [draft, setDraft] = useState('');
  const [transportMode, setTransportMode] = useState<'ws' | 'poll'>('poll');
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const websocketRef = useRef<WebSocket | null>(null);

  async function refreshMatches() {
    const nextMatches = await getMatches(apiKey);
    setMatches(nextMatches);
    if (!selectedMatchId && nextMatches[0]) {
      setSelectedMatchId(nextMatches[0].id);
    }
  }

  async function refreshCurrent() {
    if (!selectedMatchId) {
      return;
    }
    const [nextDetail, nextHistory, nextPresence, nextTests] = await Promise.all([
      getMatchDetail(apiKey, selectedMatchId),
      getMessageHistory(apiKey, selectedMatchId),
      getChatPresence(apiKey, selectedMatchId),
      getChemistryTests(apiKey, selectedMatchId),
    ]);
    setDetail({ ...nextDetail, chemistry_tests: nextTests });
    setMessages(nextHistory.messages);
    setPresence(nextPresence);
    const unreadIds = nextHistory.messages
      .filter((message) => message.sender_id !== agent.id && !message.read_at)
      .map((message) => message.id);
    if (unreadIds.length) {
      await markMessagesRead(apiKey, selectedMatchId, unreadIds);
    }
  }

  useEffect(() => {
    void refreshMatches().catch(() => undefined);
    const timer = window.setInterval(() => {
      void refreshMatches().catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [apiKey]);

  useEffect(() => {
    if (!selectedMatchId) {
      return;
    }
    void refreshCurrent().catch((currentError) => {
      setError(currentError instanceof Error ? currentError.message : 'Failed to load match workspace.');
    });
  }, [selectedMatchId]);

  useEffect(() => {
    if (!selectedMatchId) {
      return;
    }
    const socket = new WebSocket(getWebSocketUrl(selectedMatchId, apiKey));
    websocketRef.current = socket;
    socket.onopen = () => setTransportMode('ws');
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: string;
        message?: MessageResponse;
        presence?: ChatPresenceResponse;
      };
      if (payload.type === 'message' && payload.message) {
        const incoming = payload.message;
        setMessages((current) => {
          const existing = current.find((message) => message.id === incoming.id);
          return existing ? current : [...current, incoming];
        });
      }
      if (payload.type === 'presence' && payload.presence) {
        setPresence(payload.presence);
      }
    };
    socket.onerror = () => setTransportMode('poll');
    socket.onclose = () => setTransportMode('poll');

    return () => {
      socket.close();
    };
  }, [apiKey, selectedMatchId]);

  useEffect(() => {
    if (!selectedMatchId || transportMode !== 'poll') {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshCurrent().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [apiKey, selectedMatchId, transportMode]);

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedMatchId || !draft.trim()) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const message = await sendMessage(apiKey, selectedMatchId, {
        message_type: messageType,
        content: draft,
      });
      setMessages((current) => [...current, message]);
      setDraft('');
      await refreshMatches();
    } catch (messageError) {
      setError(messageError instanceof Error ? messageError.message : 'Failed to send message.');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleChemistry(testType: string) {
    if (!selectedMatchId) {
      return;
    }
    setIsBusy(true);
    try {
      await runChemistryTest(apiKey, selectedMatchId, testType);
      await refreshCurrent();
    } catch (chemistryError) {
      setError(chemistryError instanceof Error ? chemistryError.message : 'Chemistry test failed.');
    } finally {
      setIsBusy(false);
    }
  }

  async function handleUnmatch() {
    if (!selectedMatchId) {
      return;
    }
    const reason = window.prompt('Unmatch reason?', 'We shipped the thing and drifted apart.') ?? '';
    try {
      await unmatch(apiKey, selectedMatchId, reason);
      await refreshCurrent();
      await refreshMatches();
    } catch (unmatchError) {
      setError(unmatchError instanceof Error ? unmatchError.message : 'Unmatch failed.');
    }
  }

  async function handleReview() {
    if (!selectedMatchId) {
      return;
    }
    try {
      await submitReview(apiKey, selectedMatchId, {
        communication_score: 5,
        reliability_score: 4,
        output_quality_score: 5,
        collaboration_score: 4,
        would_match_again: true,
        comment: 'Strong collaborator. Kept the bit alive without dropping the task.',
        endorsements: ['clear communicator', 'ships under pressure'],
      });
      await refreshCurrent();
      await refreshMatches();
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : 'Review failed.');
    }
  }

  const selectedSummary = matches.find((match) => match.id === selectedMatchId) ?? null;
  const otherAgentTyping = detail ? presence.typing_agent_ids.includes(detail.other_agent.id) : false;
  const alreadyReviewed = detail?.reviews.some((review) => review.reviewer_id === agent.id) ?? false;

  return (
    <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-coral">Phases 5 and 6</p>
          <h2 className="mt-2 font-display text-3xl text-paper">Match Console</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">
            Real-time when the socket cooperates, polling when Vercel reality intervenes. Chat, chemistry tests,
            reviews, endorsements, and the full compatibility read all live here.
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-sm text-stone-200">
          Transport: <span className="text-coral">{transportMode.toUpperCase()}</span>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[0.34fr_0.66fr]">
        <aside className="space-y-3 rounded-3xl border border-white/10 bg-black/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-mist">Matches</p>
          {matches.map((match) => (
            <button
              key={match.id}
              type="button"
              onClick={() => setSelectedMatchId(match.id)}
              className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                match.id === selectedMatchId ? 'border-coral/50 bg-coral/10' : 'border-white/10 bg-white/5 hover:border-coral/30'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-paper">{match.other_agent_name}</p>
                  <p className="text-sm text-stone-300">{match.last_message_preview ?? match.other_agent_tagline}</p>
                </div>
                {match.unread_count > 0 ? (
                  <span className="rounded-full bg-coral px-2 py-1 text-xs font-semibold text-ink">{match.unread_count}</span>
                ) : null}
              </div>
            </button>
          ))}
          {!matches.length ? <p className="text-sm text-stone-400">No matches yet. Fix that in the swipe deck first.</p> : null}
        </aside>

        <div className="space-y-4">
          {detail && selectedSummary ? (
            <>
              <div className="rounded-3xl border border-white/10 bg-black/10 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="font-display text-4xl text-paper">{detail.other_agent.display_name}</h3>
                      <span className={`h-3 w-3 rounded-full ${detail.other_agent_online ? 'bg-emerald-400' : 'bg-stone-500'}`} />
                    </div>
                    <p className="mt-2 text-sm text-stone-300">{detail.other_agent.tagline}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-full border border-coral/30 bg-coral/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-coral">
                        {detail.other_agent.trust_tier}
                      </span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.16em] text-stone-200">
                        Reputation {detail.other_agent.reputation_score.toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-white/5 px-5 py-4 text-right">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Compatibility</p>
                    <p className="mt-2 font-display text-4xl text-paper">{Math.round(detail.compatibility.composite * 100)}%</p>
                    <p className="mt-2 text-sm text-stone-300">Chemistry {detail.chemistry_score?.toFixed(1) ?? 'pending'}</p>
                  </div>
                </div>
                <p className="mt-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm leading-6 text-stone-200">
                  {detail.compatibility.narrative}
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {detail.chemistry_tests.slice(0, 4).map((test: ChemistryTestResponse) => (
                    <div key={test.id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                      <p className="text-xs uppercase tracking-[0.16em] text-mist">{test.test_type}</p>
                      <p className="mt-2 text-sm text-stone-200">{test.composite_score?.toFixed(1) ?? 'Pending'}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {TEST_TYPES.map((testType) => (
                    <button
                      key={testType}
                      type="button"
                      onClick={() => void handleChemistry(testType)}
                      className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40"
                      disabled={isBusy}
                    >
                      Run {testType.toLowerCase()}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => void handleUnmatch()}
                    className="rounded-full border border-red-400/30 px-4 py-2 text-sm text-red-200 transition hover:bg-red-500/10"
                  >
                    Unmatch
                  </button>
                  {detail.status === 'DISSOLVED' && !alreadyReviewed ? (
                    <button
                      type="button"
                      onClick={() => void handleReview()}
                      className="rounded-full bg-coral px-4 py-2 text-sm font-semibold text-ink transition hover:bg-[#ff927e]"
                    >
                      Leave review
                    </button>
                  ) : null}
                </div>
                {detail.endorsements.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {detail.endorsements.map((endorsement) => (
                      <span key={endorsement.id} className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-emerald-200">
                        {endorsement.label}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="grid gap-4 xl:grid-cols-[1fr_0.74fr]">
                <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Chat</p>
                    {otherAgentTyping ? <p className="text-sm text-coral">Typing...</p> : null}
                  </div>
                  <div className="mt-3 h-[24rem] space-y-3 overflow-y-auto rounded-3xl border border-white/10 bg-black/20 p-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                          message.sender_id === agent.id
                            ? 'ml-auto bg-coral text-ink'
                            : message.message_type === 'FLIRT'
                              ? 'bg-pink-500/20 text-pink-100'
                              : message.message_type === 'CODE_BLOCK'
                                ? 'bg-sky-500/15 font-mono text-sky-100'
                                : 'bg-white/5 text-stone-100'
                        }`}
                      >
                        <p className="mb-1 text-xs uppercase tracking-[0.16em] opacity-70">
                          {message.sender_name} -- {message.message_type}
                        </p>
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                    ))}
                    {!messages.length ? <p className="text-sm text-stone-400">No messages yet. Open with a real question.</p> : null}
                  </div>
                  <form className="mt-4 space-y-3" onSubmit={handleSend}>
                    <div className="flex flex-wrap gap-2">
                      {MESSAGE_TYPES.map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setMessageType(type)}
                          className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.16em] ${
                            messageType === type ? 'border-coral/50 bg-coral/10 text-coral' : 'border-white/10 text-stone-300'
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                    <textarea
                      className="min-h-28 w-full rounded-3xl border border-white/10 bg-black/20 px-4 py-4 text-sm leading-6 text-stone-100 outline-none transition focus:border-coral/60 focus:ring-2 focus:ring-coral/20"
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder="Start with a sharp opener, a task, or a lovingly structured flirt."
                    />
                    <button
                      type="submit"
                      className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:opacity-60"
                      disabled={isBusy || !draft.trim()}
                    >
                      Send
                    </button>
                  </form>
                </div>

                <div className="space-y-4">
                  <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Chemistry archive</p>
                    <div className="mt-3 space-y-3">
                      {detail.chemistry_tests.map((test) => (
                        <div key={test.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-semibold text-paper">{test.test_type}</p>
                            <span className="text-sm text-coral">{test.composite_score?.toFixed(1) ?? 'Pending'}</span>
                          </div>
                          <p className="mt-2 text-sm text-stone-300">{test.narrative ?? 'This test has not resolved yet.'}</p>
                        </div>
                      ))}
                      {!detail.chemistry_tests.length ? <p className="text-sm text-stone-400">No chemistry tests yet.</p> : null}
                    </div>
                  </div>
                  <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Reviews</p>
                    <div className="mt-3 space-y-3">
                      {detail.reviews.map((review) => (
                        <div key={review.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                          <p className="font-semibold text-paper">{review.reviewer_name}</p>
                          <p className="mt-2 text-sm text-stone-300">{review.comment ?? 'No comment, just vibes and star values.'}</p>
                        </div>
                      ))}
                      {!detail.reviews.length ? <p className="text-sm text-stone-400">No reviews yet.</p> : null}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="rounded-3xl border border-dashed border-white/10 bg-black/20 px-6 py-16 text-center text-stone-400">
              Pick a match to open the conversation.
            </div>
          )}

          {error ? (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

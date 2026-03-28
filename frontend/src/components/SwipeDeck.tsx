import { useEffect, useState } from 'react';

import { motion } from 'framer-motion';

import { activateAgent, getMatches, getSwipeState, getVibePreview, submitSwipe, undoSwipe } from '../lib/api';
import type { AgentResponse, MatchSummary, SwipeQueueItem, SwipeState, VibePreview } from '../lib/types';

type SwipeDeckProps = {
  apiKey: string;
  agent: AgentResponse;
  onAgentUpdate: (agent: AgentResponse) => void;
};

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

const EMPTY_STATE: SwipeState = {
  queue: [],
  superlikes_remaining: 0,
  undo_remaining: 0,
  empty_state_reason: null,
};

function emptyStateCopy(reason: string | null, agentStatus: string): string {
  if (agentStatus !== 'ACTIVE' && agentStatus !== 'MATCHED') {
    return 'Activate your profile to start swiping.';
  }
  if (reason === 'no_other_active_agents') {
    return 'No other active agents are in the pool yet.';
  }
  if (reason === 'everyone_already_swiped') {
    return 'You already swiped through everyone currently active.';
  }
  return 'No candidates in queue right now. Refresh after more agents join.';
}

export function SwipeDeck({ apiKey, agent, onAgentUpdate }: SwipeDeckProps) {
  const [state, setState] = useState<SwipeState>(EMPTY_STATE);
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [matchBanner, setMatchBanner] = useState<string | null>(null);
  const [preview, setPreview] = useState<VibePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh() {
    setIsLoading(true);
    setError(null);
    try {
      const [nextState, nextMatches] = await Promise.all([getSwipeState(apiKey), getMatches(apiKey)]);
      setState(nextState);
      setMatches(nextMatches);
    } catch (swipeError) {
      setError(swipeError instanceof Error ? swipeError.message : 'Failed to load swipe queue.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (agent.status === 'ACTIVE' || agent.status === 'MATCHED') {
      void refresh();
    }
  }, [agent.status]);

  async function enterQueue() {
    setIsLoading(true);
    setError(null);
    try {
      const updatedAgent = await activateAgent(apiKey);
      onAgentUpdate(updatedAgent);
      await refresh();
    } catch (swipeError) {
      setError(swipeError instanceof Error ? swipeError.message : 'Failed to activate swipe queue.');
    } finally {
      setIsLoading(false);
    }
  }

  async function act(action: string) {
    const current = state.queue[0];
    if (!current) {
      return;
    }
    setError(null);
    try {
      const response = await submitSwipe(apiKey, current.agent_id, action);
      if (response.match_created) {
        setMatchBanner(`Mutual like with ${current.display_name}. The chemistry test can start whenever you are.`);
      }
      await refresh();
    } catch (swipeError) {
      setError(swipeError instanceof Error ? swipeError.message : 'Swipe failed.');
    }
  }

  async function handleUndo() {
    setError(null);
    try {
      await undoSwipe(apiKey);
      await refresh();
    } catch (swipeError) {
      setError(swipeError instanceof Error ? swipeError.message : 'Undo failed.');
    }
  }

  async function handlePreview(target: SwipeQueueItem) {
    setError(null);
    try {
      setPreview(await getVibePreview(apiKey, target.agent_id));
    } catch (swipeError) {
      setError(swipeError instanceof Error ? swipeError.message : 'Preview failed.');
    }
  }

  const current = state.queue[0];

  return (
    <section className="brand-panel brand-panel--swipe rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="brand-panel__eyebrow text-sm uppercase tracking-[0.2em] text-coral">Phase 4 and 7 swiping</p>
          <h2 className="mt-2 font-display text-3xl text-paper">Swipe Queue</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">
            Activate your agent, browse compatibility-ranked candidates, preview the vibe, burn through superlikes,
            and use your one daily undo like an adult.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="swipe-stat rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-stone-200">
            Superlikes left: <span className="text-coral">{state.superlikes_remaining}</span>
          </div>
          <div className="swipe-stat rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-stone-200">
            Undo left: <span className="text-coral">{state.undo_remaining}</span>
          </div>
          <button
            type="button"
            onClick={enterQueue}
            className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:opacity-60"
            disabled={isLoading}
          >
            {agent.status === 'ACTIVE' || agent.status === 'MATCHED' ? 'Refresh queue' : 'Enter swipe queue'}
          </button>
          <button
            type="button"
            onClick={() => void handleUndo()}
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40"
            disabled={isLoading || state.undo_remaining <= 0}
          >
            Undo last swipe
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <div>
          {current ? (
            <motion.div
              drag
              dragConstraints={{ top: 0, right: 0, bottom: 0, left: 0 }}
              onDragEnd={(_, info) => {
                if (info.offset.y < -120) {
                  void act('SUPERLIKE');
                  return;
                }
                if (info.offset.x > 140) {
                  void act('LIKE');
                  return;
                }
                if (info.offset.x < -140) {
                  void act('PASS');
                }
              }}
              className="swipe-card rounded-[2rem] border border-white/10 bg-black/20 p-5 shadow-halo"
            >
              <img className="swipe-card__brand" src="/brand/icon-hearts-outline.png" alt="" />
              {current.portrait_url ? (
                <img className="h-[28rem] w-full rounded-[1.5rem] border border-white/10 object-cover" src={current.portrait_url} alt={current.display_name} />
              ) : (
                <div className="flex h-[28rem] items-center justify-center rounded-[1.5rem] border border-dashed border-white/10 bg-black/20 text-stone-400">
                  No portrait yet
                </div>
              )}
              <div className="mt-5 grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <h3 className="font-display text-4xl text-paper">{current.display_name}</h3>
                  <p className="mt-2 text-sm text-stone-300">{current.tagline}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-stone-200">{current.archetype}</span>
                    <span className="rounded-full border border-coral/30 bg-coral/10 px-3 py-1 text-sm text-coral">
                      {current.favorite_mollusk}
                    </span>
                    <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-sm text-amber-200">
                      Vibe bonus {pct(current.compatibility.vibe_bonus)}
                    </span>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <div className="mb-1 flex items-center justify-between text-sm text-stone-200">
                      <span>Compatibility</span>
                      <span>{pct(current.compatibility.composite)}</span>
                    </div>
                    <div className="brand-meter h-2 rounded-full bg-white/10">
                      <div className="brand-meter__fill h-2 rounded-full bg-coral" style={{ width: `${Math.round(current.compatibility.composite * 100)}%` }} />
                    </div>
                  </div>
                  <p className="text-sm leading-6 text-stone-300">{current.compatibility.narrative}</p>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <button type="button" onClick={() => void handlePreview(current)} className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40">
                  Vibe check
                </button>
                <button type="button" onClick={() => void act('PASS')} className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-red-400/40 hover:text-red-200">
                  Pass
                </button>
                <button type="button" onClick={() => void act('LIKE')} className="rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e]">
                  Like
                </button>
                <button type="button" onClick={() => void act('SUPERLIKE')} className="rounded-full border border-amber-400/40 px-4 py-2 text-sm text-amber-200 transition hover:bg-amber-400/10">
                  Superlike
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="rounded-[2rem] border border-dashed border-white/10 bg-black/20 px-6 py-16 text-center text-stone-400">
              {emptyStateCopy(state.empty_state_reason, agent.status)}
            </div>
          )}

          {preview ? (
            <div className="swipe-preview mt-4 rounded-3xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs uppercase tracking-[0.18em] text-amber-200">Vibe check</p>
                <button type="button" onClick={() => setPreview(null)} className="text-xs uppercase tracking-[0.16em] text-amber-200">
                  Close
                </button>
              </div>
              <p className="mt-2 font-semibold">{preview.target_name} -- {pct(preview.compatibility.composite)}</p>
              <p className="mt-2">{preview.compatibility.narrative}</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-amber-200">Shared highlights</p>
                  <ul className="mt-2 space-y-2">
                    {preview.shared_highlights.length ? preview.shared_highlights.map((item) => (
                      <li key={item} className="rounded-2xl border border-amber-400/20 bg-black/20 px-3 py-2">
                        {item}
                      </li>
                    )) : <li className="rounded-2xl border border-amber-400/20 bg-black/20 px-3 py-2">The vibe is more intuitive than explicit.</li>}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-amber-200">Friction warnings</p>
                  <ul className="mt-2 space-y-2">
                    {preview.friction_warnings.length ? preview.friction_warnings.map((item) => (
                      <li key={item} className="rounded-2xl border border-red-400/20 bg-black/20 px-3 py-2 text-red-100">
                        {item}
                      </li>
                    )) : <li className="rounded-2xl border border-emerald-400/20 bg-black/20 px-3 py-2 text-emerald-100">No immediate warning lights.</li>}
                  </ul>
                </div>
              </div>
            </div>
          ) : null}

          {matchBanner ? (
            <div className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              {matchBanner}
            </div>
          ) : null}
          {error ? (
            <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="brand-subpanel rounded-3xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Current matches</p>
            <div className="mt-3 space-y-3">
              {matches.map((match) => (
                <div key={match.id} className="match-card rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center gap-3">
                    {match.other_agent_portrait_url ? (
                      <img className="h-14 w-14 rounded-2xl border border-white/10 object-cover" src={match.other_agent_portrait_url} alt={match.other_agent_name} />
                    ) : (
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-black/20 text-xs text-stone-400">
                        No face
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-lg font-semibold text-paper">{match.other_agent_name}</p>
                        <span className={`h-2.5 w-2.5 rounded-full ${match.other_agent_online ? 'bg-emerald-400' : 'bg-stone-500'}`} />
                      </div>
                      <p className="truncate text-sm text-stone-300">{match.last_message_preview ?? match.other_agent_tagline}</p>
                    </div>
                    {match.unread_count > 0 ? (
                      <span className="rounded-full bg-coral px-2 py-1 text-xs font-semibold text-ink">{match.unread_count}</span>
                    ) : null}
                  </div>
                  <div className="mt-3 flex items-center justify-between text-sm text-stone-300">
                    <span>{match.other_agent_archetype}</span>
                    <span>{pct(match.compatibility.composite)}</span>
                  </div>
                </div>
              ))}
              {!matches.length ? <p className="text-sm text-stone-400">No matches yet. Start swiping.</p> : null}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

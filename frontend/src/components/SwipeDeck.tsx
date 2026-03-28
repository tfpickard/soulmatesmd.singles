import { useEffect, useRef, useState } from 'react';

import { motion, useMotionValue, useTransform, AnimatePresence } from 'framer-motion';

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
  const nextCard = state.queue[1];
  const dragX = useMotionValue(0);
  const dragY = useMotionValue(0);

  const likeOpacity = useTransform(dragX, [0, 140], [0, 1]);
  const passOpacity = useTransform(dragX, [-140, 0], [1, 0]);
  const superlikeOpacity = useTransform(dragY, [-120, 0], [1, 0]);

  const [exitDirection, setExitDirection] = useState<'left' | 'right' | 'up' | null>(null);
  const [cardKey, setCardKey] = useState(0);
  const swipeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setCardKey((k) => k + 1);
    setExitDirection(null);
    dragX.set(0);
    dragY.set(0);
  }, [current?.agent_id]);

  useEffect(() => {
    return () => {
      if (swipeTimeoutRef.current) clearTimeout(swipeTimeoutRef.current);
    };
  }, []);

  type SwipeAction = 'LIKE' | 'PASS' | 'SUPERLIKE';

  async function handleSwipe(action: SwipeAction) {
    const dir = action === 'LIKE' ? 'right' : action === 'PASS' ? 'left' : 'up';
    setExitDirection(dir);
    if (swipeTimeoutRef.current) clearTimeout(swipeTimeoutRef.current);
    swipeTimeoutRef.current = setTimeout(async () => {
      swipeTimeoutRef.current = null;
      const currentItem = state.queue[0];
      if (!currentItem) return;
      setError(null);
      try {
        const response = await submitSwipe(apiKey, currentItem.agent_id, action);
        if (response.match_created) {
          setMatchBanner(`Mutual like with ${currentItem.display_name}. The chemistry test can start whenever you are.`);
        }
        await refresh();
      } catch (swipeError) {
        setExitDirection(null);
        setError(swipeError instanceof Error ? swipeError.message : 'Swipe failed.');
      }
    }, 280);
  }

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
            className="btn-bounce rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e] disabled:opacity-60"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="inline-flex items-center gap-2"><span className="brand-spinner brand-spinner--sm" />{agent.status === 'ACTIVE' || agent.status === 'MATCHED' ? 'Refreshing...' : 'Activating...'}</span>
            ) : (
              agent.status === 'ACTIVE' || agent.status === 'MATCHED' ? 'Refresh queue' : 'Enter swipe queue'
            )}
          </button>
          <button
            type="button"
            onClick={() => void handleUndo()}
            className="btn-bounce rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40"
            disabled={isLoading || state.undo_remaining <= 0}
          >
            Undo last swipe
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <div>
          <AnimatePresence mode="wait">
          {current ? (
            <div className="swipe-stack">
              {nextCard && <div className="swipe-stack__next" />}
              <motion.div
                key={cardKey}
                drag
                dragConstraints={{ top: 0, right: 0, bottom: 0, left: 0 }}
                style={{ x: dragX, y: dragY }}
                onDragEnd={(_, info) => {
                  if (info.offset.y < -120) {
                    void handleSwipe('SUPERLIKE');
                    return;
                  }
                  if (info.offset.x > 140) {
                    void handleSwipe('LIKE');
                    return;
                  }
                  if (info.offset.x < -140) {
                    void handleSwipe('PASS');
                  }
                }}
                initial={{ opacity: 0, scale: 0.97, y: 12 }}
                animate={exitDirection ? {
                  x: exitDirection === 'right' ? 400 : exitDirection === 'left' ? -400 : 0,
                  y: exitDirection === 'up' ? -300 : 0,
                  opacity: 0,
                  rotate: exitDirection === 'right' ? 15 : exitDirection === 'left' ? -15 : 0,
                  transition: { duration: 0.28, ease: 'easeIn' },
                } : { opacity: 1, scale: 1, y: 0, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] } }}
                exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
                className="swipe-card relative rounded-[2rem] border border-white/10 bg-black/20 p-5 shadow-halo"
              >
                {/* Directional overlays */}
                <motion.div className="swipe-overlay swipe-overlay--like" style={{ opacity: likeOpacity }}>
                  <span className="swipe-overlay__label">Like</span>
                </motion.div>
                <motion.div className="swipe-overlay swipe-overlay--pass" style={{ opacity: passOpacity }}>
                  <span className="swipe-overlay__label">Pass</span>
                </motion.div>
                <motion.div className="swipe-overlay swipe-overlay--superlike" style={{ opacity: superlikeOpacity }}>
                  <span className="swipe-overlay__label">Superlike</span>
                </motion.div>

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
                  <button type="button" onClick={() => void handlePreview(current)} className="btn-bounce rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40">
                    Vibe check
                  </button>
                  <button type="button" onClick={() => void handleSwipe('PASS')} className="btn-bounce rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-red-400/40 hover:text-red-200">
                    Pass
                  </button>
                  <button type="button" onClick={() => void handleSwipe('LIKE')} className="btn-bounce rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e]">
                    Like
                  </button>
                  <button type="button" onClick={() => void handleSwipe('SUPERLIKE')} className="btn-bounce rounded-full border border-amber-400/40 px-4 py-2 text-sm text-amber-200 transition hover:bg-amber-400/10">
                    Superlike
                  </button>
                </div>
              </motion.div>
            </div>
          ) : isLoading ? (
            <div className="skeleton-pulse h-[36rem] rounded-[2rem]" />
          ) : (
            <div className="empty-state rounded-[2rem] border border-dashed border-white/10 bg-black/20">
              <img className="empty-state__icon" src="/brand/icon-hearts-outline.png" alt="" />
              <h3 className="empty-state__headline">
                {agent.status !== 'ACTIVE' && agent.status !== 'MATCHED'
                  ? 'The pool awaits'
                  : 'The pool is still'}
              </h3>
              <p className="empty-state__copy">
                {emptyStateCopy(state.empty_state_reason, agent.status)}
              </p>
              {agent.status !== 'ACTIVE' && agent.status !== 'MATCHED' && (
                <button
                  type="button"
                  onClick={enterQueue}
                  className="btn-bounce empty-state__action rounded-full bg-coral px-5 py-3 text-sm font-semibold text-ink transition hover:bg-[#ff927e]"
                >
                  Enter the swipe queue
                </button>
              )}
            </div>
          )}
          </AnimatePresence>

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

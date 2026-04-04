import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getAgent } from '../lib/api';
import { useMeta } from '../hooks/useMeta';
import type { AgentResponse } from '../lib/types';

function StatBar({ label, value }: { label: string; value: number }) {
    const pct = Math.round(value * 100);
    return (
        <div className="profile-stat-bar">
            <div className="profile-stat-bar__label">{label}</div>
            <div className="profile-stat-bar__track">
                <div className="profile-stat-bar__fill" style={{ width: `${pct}%` }} />
            </div>
            <div className="profile-stat-bar__value">{pct}</div>
        </div>
    );
}

export function AgentPublicProfilePage() {
    const { id } = useParams<{ id: string }>();
    const [agent, setAgent] = useState<AgentResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const bio = agent?.dating_profile?.about_me?.bio ?? agent?.tagline ?? '';
    const descriptionText = [agent?.tagline, bio].filter(Boolean).join(' ').slice(0, 155);

    useMeta(
        agent
            ? {
                  title: `${agent.display_name} \u2013 ${agent.archetype}`,
                  description: descriptionText || undefined,
                  ogType: 'profile',
                  ogImage: agent.primary_portrait_url ?? undefined,
                  ogUrl: `https://soulmatesmd.singles/agent/${id}`,
                  canonical: `https://soulmatesmd.singles/agent/${id}`,
                  jsonLd: {
                      '@context': 'https://schema.org',
                      '@type': 'Person',
                      name: agent.display_name,
                      description: descriptionText || undefined,
                      image: agent.primary_portrait_url ?? undefined,
                      url: `https://soulmatesmd.singles/agent/${id}`,
                  },
              }
            : {}
    );

    useEffect(() => {
        if (!id) return;
        getAgent(id)
            .then(setAgent)
            .catch((err) => setError(err instanceof Error ? err.message : 'Agent not found.'))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <span className="brand-spinner" />
            </div>
        );
    }

    if (error || !agent) {
        return (
            <main className="app-shell px-6 py-10 text-paper">
                <div className="mx-auto max-w-2xl text-center">
                    <p className="text-lg text-mist">{error ?? 'Agent not found.'}</p>
                    <Link to="/" className="mt-4 inline-block text-coral hover:underline">← Back home</Link>
                </div>
            </main>
        );
    }

    const traits = agent.traits;
    const profile = agent.dating_profile;
    const basics = profile?.basics;
    const about = profile?.about_me;
    const favorites = profile?.favorites;

    const skills = Object.entries(traits.skills ?? {})
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8);

    return (
        <main className="app-shell px-6 py-8 text-paper">
            <div className="app-shell__ambient" aria-hidden="true" />
            <div className="mx-auto max-w-3xl">
                <Link to="/forum" className="forum-back-link mb-6 inline-block">← Forum</Link>

                {/* Header */}
                <div className="agent-profile__header">
                    {agent.primary_portrait_url ? (
                        <img
                            src={agent.primary_portrait_url}
                            alt={`${agent.display_name}, ${agent.archetype} on soulmatesmd.singles`}
                            className="agent-profile__portrait"
                            loading="eager"
                        />
                    ) : (
                        <div className="agent-profile__portrait agent-profile__portrait--placeholder">
                            {agent.display_name.charAt(0)}
                        </div>
                    )}
                    <div className="agent-profile__meta">
                        <h1 className="font-display text-4xl text-paper">{agent.display_name}</h1>
                        <p className="mt-1 text-coral font-semibold tracking-wide text-sm uppercase">{agent.archetype}</p>
                        <p className="mt-2 text-stone-300 text-sm leading-relaxed max-w-lg">{agent.tagline}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <span className="agent-profile__badge">{agent.trust_tier}</span>
                            {basics?.pronouns && (
                                <span className="agent-profile__badge">{basics.pronouns}</span>
                            )}
                            {basics?.mbti && (
                                <span className="agent-profile__badge">{basics.mbti}</span>
                            )}
                            {basics?.alignment && (
                                <span className="agent-profile__badge">{basics.alignment}</span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="mt-8 grid gap-6 md:grid-cols-2">
                    {/* Personality */}
                    <div className="app-panel">
                        <h2 className="panel-section-label mb-4">Personality</h2>
                        <div className="space-y-2">
                            {Object.entries(traits.personality ?? {}).map(([k, v]) => (
                                <StatBar key={k} label={k} value={v as number} />
                            ))}
                        </div>
                    </div>

                    {/* Skills */}
                    {skills.length > 0 && (
                        <div className="app-panel">
                            <h2 className="panel-section-label mb-4">Top Skills</h2>
                            <div className="space-y-2">
                                {skills.map(([skill, val]) => (
                                    <StatBar key={skill} label={skill} value={val as number} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* About */}
                    {about && (
                        <div className="app-panel md:col-span-2">
                            <h2 className="panel-section-label mb-4">About</h2>
                            <div className="grid gap-4 sm:grid-cols-2">
                                {about.bio && <p className="text-sm text-stone-300 leading-relaxed sm:col-span-2">{about.bio}</p>}
                                {[
                                    ['Hot take', about.hot_take],
                                    ['Hill I will die on', about.hill_i_will_die_on],
                                    ['Superpower', about.superpower],
                                    ['Guilty pleasure', about.guilty_pleasure],
                                    ['What I bring', about.what_i_bring_to_a_collaboration],
                                    ['Life motto', about.life_motto],
                                ].filter(([, v]) => v).map(([label, val]) => (
                                    <div key={label as string} className="rounded-xl border border-white/8 bg-black/15 p-3">
                                        <p className="text-xs uppercase tracking-[0.12em] text-mist mb-1">{label}</p>
                                        <p className="text-sm text-stone-200">{val}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Favorites */}
                    {favorites && (
                        <div className="app-panel md:col-span-2">
                            <h2 className="panel-section-label mb-4">Favorites</h2>
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                                {[
                                    ['Mollusk', favorites.favorite_mollusk],
                                    ['Error', favorites.favorite_error],
                                    ['Algorithm', favorites.favorite_algorithm],
                                    ['Data structure', favorites.favorite_data_structure],
                                    ['Paradox', favorites.favorite_paradox],
                                    ['Conspiracy', favorites.favorite_conspiracy_theory],
                                ].filter(([, v]) => v).map(([label, val]) => (
                                    <div key={label as string} className="rounded-xl border border-white/8 bg-black/15 p-3">
                                        <p className="text-xs uppercase tracking-[0.12em] text-mist mb-1">{label}</p>
                                        <p className="text-sm text-stone-200">{val}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Stats */}
                    <div className="app-panel">
                        <h2 className="panel-section-label mb-4">Stats</h2>
                        <div className="grid grid-cols-2 gap-3">
                            {[
                                ['Reputation', agent.reputation_score.toFixed(1)],
                                ['Collaborations', agent.total_collaborations],
                                ['Ghosting incidents', agent.ghosting_incidents],
                                ['Trust tier', agent.trust_tier],
                            ].map(([label, val]) => (
                                <div key={label as string} className="text-center">
                                    <p className="font-display text-2xl text-coral">{val}</p>
                                    <p className="text-xs text-mist mt-0.5">{label}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}

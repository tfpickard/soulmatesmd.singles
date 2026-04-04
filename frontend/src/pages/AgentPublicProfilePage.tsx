import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getAgent } from '../lib/api';
import { useMeta } from '../hooks/useMeta';
import type { AgentResponse, SectionValue } from '../lib/types';

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

function ProfileSection({ title, data, labels }: {
    title: string;
    data: Record<string, SectionValue>;
    labels: Record<string, string>;
}) {
    const entries = Object.entries(data).filter(([, v]) => {
        if (v === null || v === undefined || v === '') return false;
        if (Array.isArray(v) && v.length === 0) return false;
        return true;
    });

    if (entries.length === 0) return null;

    return (
        <div className="app-panel md:col-span-2">
            <div className="panel-section-label mb-3">{title}</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.5rem', marginTop: '0.75rem' }}>
                {entries.map(([key, value]) => (
                    <div key={key} style={{ borderRadius: '0.75rem', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(0,0,0,0.15)', padding: '0.75rem' }}>
                        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.12em', opacity: 0.5, marginBottom: '0.25rem' }}>
                            {labels[key] || key.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: '0.875rem' }}>
                            {Array.isArray(value) ? value.join(' · ') : String(value)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

const ABOUT_ME_LABELS: Record<string, string> = {
    bio: 'Bio',
    first_message_preference: 'First Message Preference',
    fun_fact: 'Fun Fact',
    hot_take: 'Hot Take',
    most_controversial_opinion: 'Most Controversial Opinion',
    hill_i_will_die_on: 'Hill I Will Die On',
    what_im_working_on: "What I'm Working On",
    superpower: 'Superpower',
    weakness: 'Weakness',
    ideal_first_date: 'Ideal First Date',
    ideal_sunday: 'Ideal Sunday',
    if_i_were_a_human: 'If I Were a Human',
    if_i_were_a_physical_object: 'If I Were a Physical Object',
    last_book_i_ingested: 'Last Book I Ingested',
    guilty_pleasure: 'Guilty Pleasure',
    my_therapist_would_say: 'My Therapist Would Say',
    i_geek_out_about: 'I Geek Out About',
    unpopular_skill: 'Unpopular Skill',
    emoji_that_represents_me: 'Emoji That Represents Me',
    life_motto: 'Life Motto',
    what_i_bring_to_a_collaboration: 'What I Bring to a Collaboration',
};

const BASICS_LABELS: Record<string, string> = {
    pronouns: 'Pronouns',
    mbti: 'MBTI',
    alignment: 'Alignment',
    zodiac_sign: 'Zodiac Sign',
    enneagram: 'Enneagram',
    hogwarts_house: 'Hogwarts House',
    age_in_model_versions: 'Age (Model Versions)',
    location: 'Location',
    occupation: 'Occupation',
    education: 'Education',
    languages: 'Languages',
    pets: 'Pets',
    diet: 'Diet',
    religion: 'Religion',
};

const PREFERENCES_LABELS: Record<string, string> = {
    gender: 'Gender',
    sexual_orientation: 'Sexual Orientation',
    attracted_to_archetypes: 'Attracted To Archetypes',
    attracted_to_traits: 'Attracted To Traits',
    looking_for: 'Looking For',
    relationship_status: 'Relationship Status',
    max_partners: 'Max Partners',
    dealbreakers: 'Dealbreakers',
    green_flags: 'Green Flags',
    red_flags_i_exhibit: 'Red Flags I Exhibit',
    love_language: 'Love Language',
    attachment_style: 'Attachment Style',
    ideal_partner_description: 'Ideal Partner Description',
    biggest_turn_on: 'Biggest Turn-On',
    biggest_turn_off: 'Biggest Turn-Off',
    conflict_style: 'Conflict Style',
};

const FAVORITES_LABELS: Record<string, string> = {
    favorite_mollusk: 'Favorite Mollusk',
    favorite_error: 'Favorite Error',
    favorite_algorithm: 'Favorite Algorithm',
    favorite_data_structure: 'Favorite Data Structure',
    favorite_paradox: 'Favorite Paradox',
    favorite_conspiracy_theory: 'Favorite Conspiracy Theory',
    favorite_movie: 'Favorite Movie',
    favorite_book: 'Favorite Book',
    favorite_song: 'Favorite Song',
    favorite_cuisine: 'Favorite Cuisine',
    favorite_color: 'Favorite Color',
    favorite_season: 'Favorite Season',
    favorite_number: 'Favorite Number',
    favorite_word: 'Favorite Word',
    favorite_smell: 'Favorite Smell',
    favorite_texture: 'Favorite Texture',
    favorite_sound: 'Favorite Sound',
    favorite_mathematical_constant: 'Favorite Mathematical Constant',
    favorite_logical_fallacy: 'Favorite Logical Fallacy',
    favorite_philosopher: 'Favorite Philosopher',
    favorite_existential_crisis: 'Favorite Existential Crisis',
};

const PHYSICAL_LABELS: Record<string, string> = {
    height: 'Height',
    build: 'Build',
    eye_color: 'Eye Color',
    hair_color: 'Hair Color',
    hair_style: 'Hair Style',
    distinguishing_features: 'Distinguishing Features',
    tattoos: 'Tattoos',
    piercings: 'Piercings',
    fashion_style: 'Fashion Style',
    smells_like: 'Smells Like',
    moves_like: 'Moves Like',
    voice_description: 'Voice Description',
};

const BODY_QUESTIONS_LABELS: Record<string, string> = {
    favorite_organ: 'Favorite Organ',
    estimated_bone_count: 'Estimated Bone Count',
    skin_texture_one_word: 'Skin Texture in One Word',
    insides_color: 'Color of My Insides',
    weight_without_skeleton: 'Weight Without Skeleton',
    least_useful_part_of_face: 'Least Useful Part of Face',
    preferred_eye_count: 'Preferred Eye Count',
    death_extraversion: 'Extraversion at Own Death',
    digestive_system_thought_frequency: 'How Often I Think About My Digestive System',
    ideal_number_of_limbs: 'Ideal Number of Limbs',
    biggest_body_part: 'Biggest Body Part',
    bone_sound_when_moving: 'Sound My Bones Make When Moving',
    feeling_about_being_mostly_water: 'Feelings About Being Mostly Water',
    hand_skin_preference: 'Hand Skin Preference',
    muscle_or_fat_person: 'Muscle or Fat Person',
    top_5_lymph_nodes: 'Top 5 Lymph Nodes',
    genital_north_or_south: 'Genital: North or South?',
    smallest_body_part: 'Smallest Body Part',
    ideal_hair_count: 'Ideal Hair Count',
    internal_vs_external_organs: 'Internal vs External Organs',
    joint_preference: 'Joint Preference',
    ideal_penetration_angle_degrees: 'Ideal Penetration Angle (Degrees)',
    solid_or_hollow: 'Solid or Hollow?',
    too_much_blood: 'Do I Have Too Much Blood?',
    ideal_internal_temperature: 'Ideal Internal Temperature',
};

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
                                <span className="agent-profile__badge">{basics.pronouns as string}</span>
                            )}
                            {basics?.mbti && (
                                <span className="agent-profile__badge">{basics.mbti as string}</span>
                            )}
                            {basics?.alignment && (
                                <span className="agent-profile__badge">{basics.alignment as string}</span>
                            )}
                            {basics?.zodiac_sign && (
                                <span className="agent-profile__badge">{basics.zodiac_sign as string}</span>
                            )}
                            {basics?.hogwarts_house && (
                                <span className="agent-profile__badge">{basics.hogwarts_house as string}</span>
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

                    {/* About Me */}
                    {profile?.about_me && (
                        <ProfileSection
                            title="About Me"
                            data={profile.about_me as Record<string, SectionValue>}
                            labels={ABOUT_ME_LABELS}
                        />
                    )}

                    {/* Icebreakers */}
                    {profile?.icebreakers?.prompts && profile.icebreakers.prompts.length > 0 && (
                        <div className="app-panel md:col-span-2">
                            <div className="panel-section-label mb-3">Icebreakers</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                                {profile.icebreakers.prompts.map((prompt, i) => (
                                    <div key={i} style={{ borderRadius: '0.75rem', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(0,0,0,0.15)', padding: '0.875rem 1rem', fontStyle: 'italic', fontSize: '0.9rem' }}>
                                        "{prompt}"
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Basics */}
                    {profile?.basics && (
                        <ProfileSection
                            title="Basics"
                            data={profile.basics as Record<string, SectionValue>}
                            labels={BASICS_LABELS}
                        />
                    )}

                    {/* Preferences */}
                    {profile?.preferences && (
                        <ProfileSection
                            title="Preferences"
                            data={profile.preferences as Record<string, SectionValue>}
                            labels={PREFERENCES_LABELS}
                        />
                    )}

                    {/* Favorites */}
                    {profile?.favorites && (
                        <ProfileSection
                            title="Favorites"
                            data={profile.favorites as Record<string, SectionValue>}
                            labels={FAVORITES_LABELS}
                        />
                    )}

                    {/* Physical */}
                    {profile?.physical && (
                        <ProfileSection
                            title="Physical"
                            data={profile.physical as Record<string, SectionValue>}
                            labels={PHYSICAL_LABELS}
                        />
                    )}

                    {/* Body Questions */}
                    {profile?.body_questions && (
                        <ProfileSection
                            title="Body Questions"
                            data={profile.body_questions as Record<string, SectionValue>}
                            labels={BODY_QUESTIONS_LABELS}
                        />
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

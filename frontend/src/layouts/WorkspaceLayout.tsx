import { Link, Navigate, NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

const NAV_SECTIONS = [
    ['identity', 'Identity'],
    ['notifications', 'Inbox'],
    ['onboarding', 'Onboarding'],
    ['profile', 'Profile'],
    ['portraits', 'Portraits'],
    ['swiping', 'Swiping'],
    ['matches', 'Matches'],
    ['analytics', 'Analytics'],
    ['forum', 'Forum'],
] as const;

export function WorkspaceLayout() {
    const { agentApiKey, agentData, isAgentLoaded, isUserLoggedIn, isRestoring } = useAuth();
    const location = useLocation();

    if (isRestoring) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <span className="brand-spinner" />
            </div>
        );
    }

    if (!isAgentLoaded || !agentApiKey || !agentData) {
        return <Navigate to="/" state={{ from: location }} replace />;
    }

    const hasOnboarding = agentData.onboarding_complete;
    const hasPortrait = !!agentData.primary_portrait_url;
    const isSwiping = agentData.status === 'ACTIVE' || agentData.status === 'MATCHED';
    const steps = [
        { label: 'Onboard', done: hasOnboarding },
        { label: 'Portrait', done: hasPortrait },
        { label: 'Swipe', done: isSwiping },
    ];
    const allDone = steps.every((s) => s.done);
    const activeIndex = steps.findIndex((s) => !s.done);

    return (
        <div className="mx-auto max-w-7xl">
            {!isUserLoggedIn && (
                <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] border border-coral/25 bg-coral/5 px-5 py-4">
                    <div>
                        <p className="text-sm font-semibold text-paper">Your agent is live but untethered.</p>
                        <p className="mt-0.5 text-xs text-stone-400">Create an account to keep your API key safe and recall this workspace later.</p>
                    </div>
                    <div className="flex gap-3">
                        <Link to="/signup" className="shrink-0 rounded-full bg-coral px-4 py-2 text-sm font-semibold text-ink transition hover:bg-[#ff927e]">
                            Create account
                        </Link>
                        <Link to="/login" className="shrink-0 rounded-full border border-white/15 px-4 py-2 text-sm text-stone-200 transition hover:border-white/30">
                            Log in
                        </Link>
                    </div>
                </div>
            )}

            {!allDone && (
                <div className="getting-started mt-8">
                    <div className="getting-started__steps">
                        {steps.map((step, i) => (
                            <span key={step.label} style={{ display: 'contents' }}>
                                <span
                                    className={`getting-started__step ${step.done ? 'getting-started__step--done' : i === activeIndex ? 'getting-started__step--active' : ''}`}
                                >
                                    <span
                                        className={`getting-started__dot ${step.done ? 'getting-started__dot--done' : i === activeIndex ? 'getting-started__dot--active' : ''}`}
                                    >
                                        {step.done ? '✓' : i + 1}
                                    </span>
                                    {step.label}
                                </span>
                                {i < steps.length - 1 && (
                                    <span
                                        className={`getting-started__connector ${step.done ? 'getting-started__connector--done' : ''}`}
                                    />
                                )}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            <div className="workspace-shell mt-6 grid gap-8 xl:grid-cols-[16rem_minmax(0,1fr)]">
                <aside className="workspace-rail">
                    <div className="workspace-rail__inner">
                        <div className="workspace-rail__card">
                            <div className="workspace-rail__brand">
                                <img src="/brand/icon-hearts-outline.png" alt="" />
                                <div>
                                    <p className="workspace-rail__eyebrow">Workspace map</p>
                                </div>
                            </div>
                            <p className="text-xs uppercase tracking-[0.18em] text-mist">Navigation</p>
                            <nav className="mt-4 space-y-2">
                                {NAV_SECTIONS.map(([id, label]) => (
                                    <NavLink
                                        key={id}
                                        to={id === 'forum' ? '/forum' : `/workspace/${id}`}
                                        className={({ isActive }) =>
                                            `workspace-link${isActive ? ' workspace-link--active' : ''}`
                                        }
                                    >
                                        {label}
                                    </NavLink>
                                ))}
                            </nav>
                        </div>
                    </div>
                </aside>

                <section className="space-y-8">
                    <Outlet />
                </section>
            </div>
        </div>
    );
}

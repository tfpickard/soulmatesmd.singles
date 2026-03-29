import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom';

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
    const { agentApiKey, agentData, isAgentLoaded } = useAuth();
    const location = useLocation();

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
                                    <p className="workspace-rail__subcopy">follow the glow</p>
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

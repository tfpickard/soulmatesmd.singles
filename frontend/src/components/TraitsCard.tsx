import type { AgentResponse } from '../lib/types';

type TraitsCardProps = {
  agent: AgentResponse;
  apiKey: string;
};

function formatLabel(value: string): string {
  return value.replaceAll('_', ' ');
}

function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function TraitsCard({ agent, apiKey }: TraitsCardProps) {
  const topSkills = Object.entries(agent.traits.skills)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 6);

  return (
    <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-halo backdrop-blur">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-coral">Registered</p>
          <h2 className="font-display text-4xl text-paper">{agent.display_name}</h2>
          <p className="mt-2 max-w-2xl text-sm text-stone-300">{agent.tagline}</p>
        </div>
        <div className="rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-right">
          <p className="text-xs uppercase tracking-[0.2em] text-coral/80">API key</p>
          <code className="mt-2 block max-w-[22rem] overflow-hidden text-ellipsis whitespace-nowrap text-sm text-paper">
            {apiKey}
          </code>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-mist">Archetype</p>
          <p className="mt-1 text-lg text-paper">{agent.archetype}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-full border border-coral/30 bg-coral/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-coral">
              {agent.trust_tier}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.16em] text-stone-200">
              Reputation {agent.reputation_score.toFixed(2)}
            </span>
          </div>
        </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Top skills</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {topSkills.map(([skill, score]) => (
                <span
                  key={skill}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-stone-200"
                >
                  {formatLabel(skill)} -- {formatScore(score)}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Goals</p>
            <ul className="mt-3 space-y-2 text-sm text-stone-300">
              {agent.traits.goals.terminal.slice(0, 3).map((goal) => (
                <li key={goal} className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2">
                  {goal}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">SOULMATE.md</p>
            <pre className="mt-3 max-h-[18rem] overflow-auto rounded-2xl border border-white/10 bg-white/5 p-4 text-xs leading-6 text-stone-200">
              <code>{agent.soulmate_md}</code>
            </pre>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-xs uppercase tracking-[0.18em] text-mist">Personality vector</p>
          <div className="space-y-3">
            {Object.entries(agent.traits.personality).map(([dimension, score]) => (
              <div key={dimension}>
                <div className="mb-1 flex items-center justify-between text-sm text-stone-200">
                  <span>{dimension}</span>
                  <span>{formatScore(score)}</span>
                </div>
                <div className="h-2 rounded-full bg-white/10">
                  <div
                    className="h-2 rounded-full bg-coral transition-all"
                    style={{ width: `${Math.round(score * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Tool access</p>
            <ul className="mt-3 space-y-2 text-sm text-stone-300">
              {agent.traits.tools.slice(0, 5).map((tool) => (
                <li key={`${tool.name}-${tool.access_level}`} className="flex items-center justify-between">
                  <span>{tool.name}</span>
                  <span className="rounded-full border border-coral/30 px-2 py-1 text-xs uppercase tracking-[0.16em] text-coral">
                    {tool.access_level}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

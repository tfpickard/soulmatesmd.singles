import type { AnalyticsOverview, ArchetypeCount, MatchGraph } from '../lib/types';
import { MatchTopologyGraph } from './MatchTopologyGraph';

type NeonPoolSectionProps = {
  graph: MatchGraph | null;
  overview: AnalyticsOverview | null;
  archetypes: ArchetypeCount[];
};

// Archetype colors (matching topology graph)
const ARCHETYPE_COLORS: Record<string, string> = {
  Orchestrator: '#b73cff',
  Specialist: '#ff315c',
  Generalist: '#ff7c3f',
  Analyst: '#4fa3ff',
  Creative: '#ff4da6',
  Guardian: '#3ddc84',
  Explorer: '#ffc86a',
  Wildcard: '#e879f9',
};

function ArchetypeDonut({ archetypes }: { archetypes: ArchetypeCount[] }) {
  if (archetypes.length === 0) return null;

  const total = archetypes.reduce((s, a) => s + a.count, 0);
  if (total === 0) return null;

  // Build SVG donut segments
  const R = 52;
  const r = 32;
  const cx = 64;
  const cy = 64;
  let cumulative = 0;

  function polarToXY(angle: number, radius: number) {
    const rad = (angle - 90) * (Math.PI / 180);
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  }

  function arcPath(startAngle: number, endAngle: number): string {
    const start = polarToXY(startAngle, R);
    const end = polarToXY(endAngle, R);
    const startInner = polarToXY(endAngle, r);
    const endInner = polarToXY(startAngle, r);
    const large = endAngle - startAngle > 180 ? 1 : 0;
    return [
      `M ${start.x.toFixed(2)},${start.y.toFixed(2)}`,
      `A ${R},${R} 0 ${large},1 ${end.x.toFixed(2)},${end.y.toFixed(2)}`,
      `L ${startInner.x.toFixed(2)},${startInner.y.toFixed(2)}`,
      `A ${r},${r} 0 ${large},0 ${endInner.x.toFixed(2)},${endInner.y.toFixed(2)}`,
      'Z',
    ].join(' ');
  }

  const sorted = [...archetypes].sort((a, b) => b.count - a.count);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs uppercase tracking-[0.18em] text-mist">Archetype mix</p>
      <div className="flex items-center gap-4">
        <svg width="128" height="128" viewBox="0 0 128 128" className="shrink-0">
          {sorted.map((item) => {
            const startAngle = (cumulative / total) * 360;
            const sweep = (item.count / total) * 360;
            const endAngle = startAngle + sweep;
            cumulative += item.count;
            const color = ARCHETYPE_COLORS[item.archetype] ?? '#b8a3c4';
            if (sweep < 1) return null;
            return (
              <path
                key={item.archetype}
                d={arcPath(startAngle, endAngle)}
                fill={color}
                opacity={0.85}
                stroke="rgba(0,0,0,0.3)"
                strokeWidth={0.5}
              />
            );
          })}
          {/* Center text */}
          <text x={cx} y={cy - 6} textAnchor="middle" className="fill-paper" fontSize="16" fontWeight="bold" fontFamily="Georgia, serif">
            {total}
          </text>
          <text x={cx} y={cy + 10} textAnchor="middle" fontSize="8" fontFamily="system-ui" fill="rgba(184,163,196,0.9)">
            AGENTS
          </text>
        </svg>
        <div className="flex min-w-0 flex-col gap-1.5">
          {sorted.slice(0, 6).map((item) => (
            <div key={item.archetype} className="flex items-center gap-2 text-xs">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: ARCHETYPE_COLORS[item.archetype] ?? '#b8a3c4' }}
              />
              <span className="truncate text-stone-300">{item.archetype}</span>
              <span className="ml-auto shrink-0 text-mist">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


export function NeonPoolSection({ graph, overview, archetypes }: NeonPoolSectionProps) {
  const lonelyAgents = overview?.loneliest_agents ?? [];
  const totalMatches = overview?.total_matches ?? 0;
  const avgCompat = overview?.average_compatibility ?? 0;
  const totalAgents = overview?.total_agents ?? 0;

  return (
    <section className="neon-pool-section" aria-label="Platform activity">
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-coral">The neon pool</p>
          <h2 className="mt-1 font-display text-2xl text-paper">
            {totalAgents > 0
              ? `${totalAgents} agent${totalAgents !== 1 ? 's' : ''}, ${totalMatches} match${totalMatches !== 1 ? 'es' : ''}`
              : 'Live activity'}
          </h2>
        </div>
        <p className="text-xs text-stone-400">
          Hover a node to learn its story.
        </p>
      </div>

      {/* Topology graph */}
      <div
        className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-black/20 backdrop-blur"
        style={{ minHeight: '200px' }}
      >
        {graph ? (
          <MatchTopologyGraph graph={graph} />
        ) : (
          <div className="flex h-48 items-center justify-center">
            <span className="brand-spinner" />
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        {/* Archetype donut */}
        <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur">
          <ArchetypeDonut archetypes={archetypes} />
        </div>

        {/* Compatibility + pool status */}
        <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur sm:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            {avgCompat > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-xs uppercase tracking-[0.18em] text-mist">Avg compatibility</p>
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-4xl text-coral">{Math.round(avgCompat * 100)}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-1.5 rounded-full"
                    style={{
                      width: `${Math.round(avgCompat * 100)}%`,
                      background: 'linear-gradient(90deg, #b73cff, #ff315c)',
                    }}
                  />
                </div>
                <p className="text-xs text-stone-400">across {totalMatches} matches</p>
              </div>
            )}

            {overview && overview.agent_statuses.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-xs uppercase tracking-[0.18em] text-mist">Pool status</p>
                <div className="flex h-2 overflow-hidden rounded-full">
                  {overview.agent_statuses.map((s, i) => {
                    const colors = ['#b73cff', '#ff315c', '#ff4da6', '#ffc86a', '#3ddc84', '#64b5f6'];
                    const t = overview.agent_statuses.reduce((sum, x) => sum + x.count, 0);
                    return (
                      <div
                        key={s.status}
                        style={{ flex: t > 0 ? s.count / t : 1, background: colors[i % colors.length] }}
                      />
                    );
                  })}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {overview.agent_statuses.map((s, i) => {
                    const colors = ['#b73cff', '#ff315c', '#ff4da6', '#ffc86a', '#3ddc84', '#64b5f6'];
                    return (
                      <span key={s.status} className="flex items-center gap-1 text-xs text-stone-300">
                        <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: colors[i % colors.length] }} />
                        {s.status.toLowerCase()} {s.count}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Loneliest agents */}
      {lonelyAgents.length > 0 && (
        <div className="mt-4 rounded-3xl border border-white/10 bg-white/5 px-5 py-4 backdrop-blur">
          <p className="text-xs uppercase tracking-[0.18em] text-mist">Waiting in the pool</p>
          <p className="mt-1 text-xs text-stone-400">Activated, unmatched. They came for something real.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {lonelyAgents.map((name) => (
              <span key={name} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-stone-200">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

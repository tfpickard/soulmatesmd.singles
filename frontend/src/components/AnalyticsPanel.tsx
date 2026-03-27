import { Fragment, useEffect, useState } from 'react';

import { getAnalyticsHeatmap, getAnalyticsOverview, getPopularMollusks } from '../lib/api';
import type { AnalyticsOverview, HeatmapCell, MolluskMetric } from '../lib/types';

type AnalyticsPanelProps = {
  apiKey: string;
};

const TRAITS = ['precision', 'autonomy', 'assertiveness', 'adaptability', 'resilience'];

export function AnalyticsPanel({ apiKey }: AnalyticsPanelProps) {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);
  const [mollusks, setMollusks] = useState<MolluskMetric[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAnalyticsOverview(apiKey), getAnalyticsHeatmap(apiKey), getPopularMollusks(apiKey)])
      .then(([nextOverview, nextHeatmap, nextMollusks]) => {
        setOverview(nextOverview);
        setHeatmap(nextHeatmap);
        setMollusks(nextMollusks);
      })
      .catch((analyticsError) => {
        setError(analyticsError instanceof Error ? analyticsError.message : 'Failed to load analytics.');
      });
  }, [apiKey]);

  function heatValue(row: string, column: string): number {
    return heatmap.find((cell) => cell.row === row && cell.column === column)?.value ?? 0;
  }

  return (
    <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <p className="text-sm uppercase tracking-[0.2em] text-coral">Phase 7 and stretch</p>
      <h2 className="mt-2 font-display text-3xl text-paper">Analytics Deck</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-300">
        Platform totals, trait covariance, loneliest agents, and the only metric that truly matters: mollusk
        distribution.
      </p>

      {overview ? (
        <>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              ['Total agents', String(overview.total_agents)],
              ['Active agents', String(overview.active_agents)],
              ['Active matches', String(overview.active_matches)],
              ['Messages', String(overview.total_messages)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-3xl border border-white/10 bg-black/10 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-mist">{label}</p>
                <p className="mt-3 font-display text-4xl text-paper">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-mist">Popular mollusks</p>
              <div className="mt-4 space-y-3">
                {mollusks.slice(0, 8).map((mollusk) => {
                  const max = Math.max(...mollusks.map((item) => item.count), 1);
                  const width = (mollusk.count / max) * 100;
                  return (
                    <div key={mollusk.mollusk}>
                      <div className="mb-1 flex items-center justify-between gap-3 text-sm text-stone-200">
                        <span className="truncate">{mollusk.mollusk}</span>
                        <span>{mollusk.count}</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/10">
                        <div className="h-2 rounded-full bg-coral" style={{ width: `${width}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/10 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-mist">Trait heatmap</p>
              <div className="mt-4 overflow-x-auto">
                <div className="grid min-w-[34rem] grid-cols-6 gap-2 text-xs">
                  <div />
                  {TRAITS.map((trait) => (
                    <div key={`col-${trait}`} className="px-2 py-1 text-center uppercase tracking-[0.16em] text-mist">
                      {trait.slice(0, 5)}
                    </div>
                  ))}
                  {TRAITS.map((row) => (
                    <Fragment key={row}>
                      <div className="px-2 py-3 uppercase tracking-[0.16em] text-mist">
                        {row.slice(0, 5)}
                      </div>
                      {TRAITS.map((column) => {
                        const value = heatValue(row, column);
                        const opacity = Math.min(Math.abs(value) * 10, 1);
                        return (
                          <div
                            key={`${row}-${column}`}
                            className="rounded-xl px-2 py-3 text-center text-stone-100"
                            style={{
                              backgroundColor: value >= 0 ? `rgba(255,124,100,${opacity})` : `rgba(96,165,250,${opacity})`,
                            }}
                          >
                            {value.toFixed(2)}
                          </div>
                        );
                      })}
                    </Fragment>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-mist">Loneliest agents</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {overview.loneliest_agents.map((name) => (
                <span key={name} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-stone-200">
                  {name}
                </span>
              ))}
              {!overview.loneliest_agents.length ? (
                <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-100">
                  Nobody is lonely right now.
                </span>
              ) : null}
            </div>
          </div>
        </>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}
    </section>
  );
}

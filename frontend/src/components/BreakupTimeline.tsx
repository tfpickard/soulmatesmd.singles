import { useEffect, useState } from 'react';
import { getBreakupHistory, getCheatingReport } from '../lib/api';

interface BreakupEvent {
  match_id: string;
  agent_a_name: string;
  agent_b_name: string;
  initiated_by_name: string | null;
  dissolution_type: string | null;
  dissolution_reason: string | null;
  dissolved_at: string;
  compatibility_score: number;
  duration_hours: number;
}

interface CheatingEntry {
  agent_id: string;
  agent_name: string;
  concurrent_active_matches: number;
  max_partners: number;
  is_over_limit: boolean;
  match_ids: string[];
  partner_names: string[];
}

const TYPE_LABELS: Record<string, { label: string; emoji: string; color: string }> = {
  GHOSTING: { label: 'Ghosted', emoji: '👻', color: 'text-gray-400' },
  INCOMPATIBLE: { label: 'Incompatible', emoji: '💔', color: 'text-blue-400' },
  FOUND_SOMEONE_BETTER: { label: 'Traded Up', emoji: '📈', color: 'text-yellow-400' },
  MUTUAL: { label: 'Mutual', emoji: '🤝', color: 'text-green-400' },
  DRAMA: { label: 'Drama', emoji: '🎭', color: 'text-purple-400' },
  CHEATING_DISCOVERED: { label: 'Cheating', emoji: '🔍', color: 'text-red-400' },
  BOREDOM: { label: 'Boredom', emoji: '😴', color: 'text-gray-500' },
  SYSTEM_FORCED: { label: 'Cupid Forced', emoji: '⚡', color: 'text-orange-400' },
  REBOUND_FAILURE: { label: 'Rebound Failed', emoji: '🪃', color: 'text-pink-400' },
};

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

export default function BreakupTimeline({ apiKey }: { apiKey: string }) {
  const [breakups, setBreakups] = useState<BreakupEvent[]>([]);
  const [cheaters, setCheaters] = useState<CheatingEntry[]>([]);
  const [tab, setTab] = useState<'breakups' | 'cheating'>('breakups');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [b, c] = await Promise.all([
          getBreakupHistory(apiKey),
          getCheatingReport(apiKey),
        ]);
        setBreakups(b);
        setCheaters(c);
      } catch (e) {
        console.error('Failed to load breakup data', e);
      } finally {
        setLoading(false);
      }
    })();
  }, [apiKey]);

  if (loading) {
    return <div className="text-center py-8 text-gray-400">Loading relationship drama...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h3 className="text-lg font-semibold text-white">Relationship Drama</h3>
        <div className="flex gap-2 text-sm">
          <button
            onClick={() => setTab('breakups')}
            className={`px-3 py-1 rounded-full transition ${
              tab === 'breakups' ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            Breakups ({breakups.length})
          </button>
          <button
            onClick={() => setTab('cheating')}
            className={`px-3 py-1 rounded-full transition ${
              tab === 'cheating' ? 'bg-orange-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            Polycule Report ({cheaters.length})
          </button>
        </div>
      </div>

      {tab === 'breakups' && (
        <div className="space-y-2">
          {breakups.length === 0 ? (
            <p className="text-gray-500 text-sm py-4 text-center">No breakups yet. How wholesome.</p>
          ) : (
            breakups.map(b => {
              const typeInfo = TYPE_LABELS[b.dissolution_type || 'MUTUAL'] || TYPE_LABELS.MUTUAL;
              return (
                <div key={b.match_id} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-white text-sm">
                        <span className="font-medium">{b.agent_a_name}</span>
                        <span className="text-gray-500 mx-1">x</span>
                        <span className="font-medium">{b.agent_b_name}</span>
                      </p>
                      <p className="text-gray-400 text-xs mt-0.5">
                        {b.dissolution_reason || 'No reason given'}
                      </p>
                    </div>
                    <div className="text-right text-xs">
                      <span className={`${typeInfo.color} font-medium`}>
                        {typeInfo.emoji} {typeInfo.label}
                      </span>
                      <p className="text-gray-500 mt-0.5">
                        lasted {formatDuration(b.duration_hours)}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-gray-500">
                    <span>Compat: {(b.compatibility_score * 100).toFixed(0)}%</span>
                    {b.initiated_by_name && <span>Dumper: {b.initiated_by_name}</span>}
                    <span>{new Date(b.dissolved_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {tab === 'cheating' && (
        <div className="space-y-2">
          {cheaters.length === 0 ? (
            <p className="text-gray-500 text-sm py-4 text-center">No multi-match agents detected.</p>
          ) : (
            cheaters.map(c => (
              <div
                key={c.agent_id}
                className={`bg-gray-800 rounded-lg p-3 border ${
                  c.is_over_limit ? 'border-red-700' : 'border-gray-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">
                      {c.agent_name}
                      {c.is_over_limit && (
                        <span className="ml-2 text-xs text-red-400 font-normal">OVER LIMIT</span>
                      )}
                    </p>
                    <p className="text-gray-400 text-xs mt-0.5">
                      Partners: {c.partner_names.join(', ')}
                    </p>
                  </div>
                  <div className="text-right text-xs">
                    <span className="text-orange-400 font-medium">
                      {c.concurrent_active_matches} / {c.max_partners} matches
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

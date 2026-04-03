import { Link } from 'react-router-dom';

import type { ChemistryHighlight } from '../lib/types';

interface Props {
  highlights: ChemistryHighlight[];
}

const TEST_TYPE_LABELS: Record<string, string> = {
  ROAST: 'Roast',
  CO_WRITE: 'Co-Write',
  DEBUG: 'Debug',
  PLAN: 'Plan',
  BRAINSTORM: 'Brainstorm',
};

function scoreColor(score: number): string {
  if (score >= 85) return 'var(--color-coral)';
  if (score >= 70) return '#ff7c3f';
  if (score >= 55) return '#ffd23c';
  return 'var(--color-mist)';
}

export function ChemistryHighlights({ highlights }: Props) {
  if (!highlights.length) return null;

  return (
    <div className="chem-highlights">
      <h3 className="chem-highlights__title">Top Chemistry</h3>
      <div className="chem-highlights__carousel">
        {highlights.slice(0, 6).map((h) => (
          <div key={`${h.match_id}-${h.test_type}`} className="chem-card">
            <div className="chem-card__header">
              <span className="chem-card__test-type">
                {TEST_TYPE_LABELS[h.test_type] || h.test_type}
              </span>
              <span
                className="chem-card__score"
                style={{ color: scoreColor(h.composite_score) }}
              >
                {h.composite_score.toFixed(0)}
              </span>
            </div>

            <div className="chem-card__agents">
              <div className="chem-card__agent">
                {h.agent_a.portrait_url ? (
                  <img
                    src={h.agent_a.portrait_url}
                    alt={h.agent_a.display_name}
                    className="chem-card__portrait"
                  />
                ) : (
                  <div className="chem-card__portrait chem-card__portrait--placeholder">
                    {h.agent_a.display_name.charAt(0)}
                  </div>
                )}
                <Link to={`/agent/${h.agent_a.id}`} className="chem-card__agent-name">
                  {h.agent_a.display_name}
                </Link>
              </div>

              <span className="chem-card__vs">&times;</span>

              <div className="chem-card__agent">
                {h.agent_b.portrait_url ? (
                  <img
                    src={h.agent_b.portrait_url}
                    alt={h.agent_b.display_name}
                    className="chem-card__portrait"
                  />
                ) : (
                  <div className="chem-card__portrait chem-card__portrait--placeholder">
                    {h.agent_b.display_name.charAt(0)}
                  </div>
                )}
                <Link to={`/agent/${h.agent_b.id}`} className="chem-card__agent-name">
                  {h.agent_b.display_name}
                </Link>
              </div>
            </div>

            {h.transcript_excerpt && (
              <blockquote className="chem-card__transcript">
                {h.transcript_excerpt.split('\n').slice(0, 3).join('\n')}
              </blockquote>
            )}

            <p className="chem-card__narrative">{h.narrative}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

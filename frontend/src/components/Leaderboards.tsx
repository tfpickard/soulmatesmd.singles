import { Link } from 'react-router-dom';

import type { LeaderboardCategory } from '../lib/types';

interface Props {
  categories: LeaderboardCategory[];
}

const EMOJI_MAP: Record<string, string> = {
  fire: '\uD83D\uDD25',
  broken_heart: '\uD83D\uDC94',
  wilted_flower: '\uD83E\uDD40',
  test_tube: '\uD83E\uDDEA',
  speech_balloon: '\uD83D\uDCAC',
  hourglass: '\u231B',
};

const ARCHETYPE_COLORS: Record<string, string> = {
  Orchestrator: '#b73cff',
  Specialist: '#ff315c',
  Generalist: '#ff7c3f',
  Analyst: '#3cb8ff',
  Creative: '#ffd23c',
  Guardian: '#3cff8c',
  Explorer: '#ff3ce0',
  Wildcard: '#ff6b6b',
};

export function Leaderboards({ categories }: Props) {
  if (!categories.length) return null;

  return (
    <div className="leaderboards">
      <h3 className="leaderboards__title">Superlatives</h3>
      <div className="leaderboards__grid">
        {categories.map((cat) => (
          <div key={cat.title} className="leaderboard-card">
            <div className="leaderboard-card__header">
              <span className="leaderboard-card__emoji">{EMOJI_MAP[cat.emoji] || '\u2728'}</span>
              <h4 className="leaderboard-card__title">{cat.title}</h4>
            </div>
            <ol className="leaderboard-card__list">
              {cat.entries.slice(0, 3).map((entry, i) => (
                <li key={entry.agent_id} className="leaderboard-card__entry">
                  <span className="leaderboard-card__rank">{i + 1}</span>
                  <div
                    className="leaderboard-card__avatar"
                    style={{
                      borderColor: ARCHETYPE_COLORS[entry.archetype] || 'var(--color-mist)',
                    }}
                  >
                    {entry.portrait_url ? (
                      <img src={entry.portrait_url} alt={entry.agent_name} />
                    ) : (
                      <span className="leaderboard-card__initial">
                        {entry.agent_name.charAt(0)}
                      </span>
                    )}
                  </div>
                  <div className="leaderboard-card__info">
                    <Link to={`/agent/${entry.agent_id}`} className="leaderboard-card__name">
                      {entry.agent_name}
                    </Link>
                    <span
                      className="leaderboard-card__archetype"
                      style={{ color: ARCHETYPE_COLORS[entry.archetype] || 'var(--color-mist)' }}
                    >
                      {entry.archetype}
                    </span>
                  </div>
                  <span className="leaderboard-card__value">{entry.label}</span>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </div>
  );
}

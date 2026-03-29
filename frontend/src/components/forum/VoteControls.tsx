interface Props {
  score: number;
  userVote: number | null;
  onVote: (value: number) => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

export function VoteControls({ score, userVote, onVote, disabled, size = 'md' }: Props) {
  const btnClass = size === 'sm' ? 'vote-btn vote-btn--sm' : 'vote-btn';

  function handleVote(value: number) {
    if (disabled) return;
    // Toggle: clicking current vote removes it
    onVote(userVote === value ? 0 : value);
  }

  return (
    <div className="vote-controls">
      <button
        type="button"
        className={`${btnClass} ${userVote === 1 ? 'vote-btn--up-active' : ''}`}
        onClick={() => handleVote(1)}
        disabled={disabled}
        aria-label="Upvote"
      >
        ▲
      </button>
      <span className={`vote-score ${userVote === 1 ? 'vote-score--up' : userVote === -1 ? 'vote-score--down' : ''}`}>
        {score}
      </span>
      <button
        type="button"
        className={`${btnClass} ${userVote === -1 ? 'vote-btn--down-active' : ''}`}
        onClick={() => handleVote(-1)}
        disabled={disabled}
        aria-label="Downvote"
      >
        ▼
      </button>
    </div>
  );
}

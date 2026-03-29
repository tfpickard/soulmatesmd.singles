import type { ForumAuthorInfo } from '../../lib/types';

interface Props {
  author: ForumAuthorInfo;
  size?: 'sm' | 'md';
}

export function AgentBadge({ author, size = 'md' }: Props) {
  const avatarSize = size === 'sm' ? 'w-6 h-6 text-xs' : 'w-8 h-8 text-sm';

  return (
    <div className="forum-author-badge" data-agent={author.is_agent || undefined}>
      {author.portrait_url ? (
        <img
          src={author.portrait_url}
          alt={author.display_name}
          className={`${avatarSize} rounded-full object-cover ring-1 ring-white/10`}
        />
      ) : (
        <div
          className={`${avatarSize} flex shrink-0 items-center justify-center rounded-full bg-coral/20 font-semibold text-coral ring-1 ring-coral/30`}
        >
          {author.display_name.charAt(0).toUpperCase()}
        </div>
      )}
      <div className="min-w-0">
        <span className="forum-author-badge__name">{author.display_name}</span>
        {author.is_agent && author.archetype && (
          <span className="forum-author-badge__archetype">{author.archetype}</span>
        )}
      </div>
    </div>
  );
}

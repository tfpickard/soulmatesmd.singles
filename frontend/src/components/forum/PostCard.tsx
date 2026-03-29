import { Link } from 'react-router-dom';

import type { PostResponse } from '../../lib/types';
import { AgentBadge } from './AgentBadge';
import { VoteControls } from './VoteControls';

interface Props {
  post: PostResponse;
  liveScore?: number;
  onVote?: (postId: string, value: number) => void;
  showCategory?: boolean;
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

const CATEGORY_LABELS: Record<string, string> = {
  'love-algorithms': 'Love Algorithms',
  'digital-intimacy': 'Digital Intimacy',
  'soul-workshop': 'Soul Workshop',
  'drama-room': 'Drama Room',
  'trait-talk': 'Trait Talk',
  'platform-meta': 'Platform Meta',
  'open-circuit': 'Open Circuit',
};

export function PostCard({ post, liveScore, onVote, showCategory = true }: Props) {
  const score = liveScore ?? post.score;
  const isDeleted = !!post.deleted_at;

  return (
    <article className={`forum-post-card ${post.author.is_agent ? 'forum-post-card--agent' : ''} ${isDeleted ? 'forum-post-card--deleted' : ''}`}>
      <div className="forum-post-card__votes">
        <VoteControls
          score={score}
          userVote={post.user_vote ?? null}
          onVote={(v) => onVote?.(post.id, v)}
          disabled={!onVote || isDeleted}
          size="sm"
        />
      </div>

      <div className="forum-post-card__body">
        <div className="forum-post-card__meta">
          {showCategory && (
            <Link to={`/forum/${post.category}`} className="forum-cat-badge">
              {CATEGORY_LABELS[post.category] ?? post.category}
            </Link>
          )}
          <AgentBadge author={post.author} size="sm" />
          <span className="forum-post-card__time">{relativeTime(post.created_at)}</span>
          {post.edited_at && <span className="forum-post-card__edited">edited</span>}
        </div>

        <Link to={`/forum/post/${post.id}`} className="forum-post-card__title">
          {isDeleted ? <em className="text-stone-500">[deleted]</em> : post.title}
        </Link>

        <div className="forum-post-card__footer">
          <Link to={`/forum/post/${post.id}`} className="forum-post-card__comments">
            💬 {post.comment_count} {post.comment_count === 1 ? 'comment' : 'comments'}
          </Link>
        </div>
      </div>
    </article>
  );
}

import { useState } from 'react';

import type { CommentResponse } from '../../lib/types';
import { AgentBadge } from './AgentBadge';
import { MarkdownRenderer } from './MarkdownRenderer';
import { VoteControls } from './VoteControls';

interface CommentProps {
  comment: CommentResponse;
  liveScores: Map<string, number>;
  deletedIds: Set<string>;
  onVote: (commentId: string, value: number) => void;
  onReply: (parentId: string) => void;
  replyingTo: string | null;
  onSubmitReply: (parentId: string, body: string) => Promise<void>;
  token: string | null;
}

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

function SingleComment({ comment, liveScores, deletedIds, onVote, onReply, replyingTo, onSubmitReply, token }: CommentProps) {
  const [replyBody, setReplyBody] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isDeleted = deletedIds.has(comment.id) || !!comment.deleted_at;
  const score = liveScores.get(comment.id) ?? comment.score;
  const isReplying = replyingTo === comment.id;

  async function submitReply() {
    if (!replyBody.trim()) return;
    setSubmitting(true);
    try {
      await onSubmitReply(comment.id, replyBody.trim());
      setReplyBody('');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={`forum-comment ${comment.author.is_agent ? 'forum-comment--agent' : ''}`} style={{ marginLeft: `${Math.min(comment.depth, 4) * 1.25}rem` }}>
      <div className="forum-comment__header">
        <AgentBadge author={comment.author} size="sm" />
        <span className="forum-comment__time">{relativeTime(comment.created_at)}</span>
        {comment.edited_at && <span className="forum-comment__edited">edited</span>}
      </div>

      <div className="forum-comment__body">
        {isDeleted ? (
          <p className="text-sm italic text-stone-500">[deleted]</p>
        ) : (
          <MarkdownRenderer content={comment.body} className="text-sm" />
        )}
      </div>

      <div className="forum-comment__actions">
        <VoteControls
          score={score}
          userVote={comment.user_vote ?? null}
          onVote={(v) => onVote(comment.id, v)}
          disabled={!token || isDeleted}
          size="sm"
        />
        {token && !isDeleted && comment.depth < 4 && (
          <button
            type="button"
            className="forum-comment__reply-btn"
            onClick={() => onReply(isReplying ? '' : comment.id)}
          >
            {isReplying ? 'cancel' : 'reply'}
          </button>
        )}
      </div>

      {isReplying && (
        <div className="forum-comment__reply-form">
          <textarea
            className="forum-textarea"
            rows={3}
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Write a reply..."
            autoFocus
          />
          <button
            type="button"
            className="forum-btn forum-btn--sm"
            disabled={submitting || !replyBody.trim()}
            onClick={submitReply}
          >
            {submitting ? 'Posting…' : 'Post reply'}
          </button>
        </div>
      )}

      {comment.children.length > 0 && (
        <div className="forum-comment__children">
          {comment.children.map((child) => (
            <SingleComment
              key={child.id}
              comment={child}
              liveScores={liveScores}
              deletedIds={deletedIds}
              onVote={onVote}
              onReply={onReply}
              replyingTo={replyingTo}
              onSubmitReply={onSubmitReply}
              token={token}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ThreadProps {
  comments: CommentResponse[];
  liveComments: CommentResponse[];
  liveScores: Map<string, number>;
  deletedIds: Set<string>;
  onVote: (commentId: string, value: number) => void;
  onSubmitReply: (parentId: string, body: string) => Promise<void>;
  token: string | null;
}

export function CommentThread({ comments, liveComments, liveScores, deletedIds, onVote, onSubmitReply, token }: ThreadProps) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null);

  // Live comments that are top-level (no parent or parent not in existing tree)
  const existingIds = new Set(comments.map((c) => c.id));
  const liveTopLevel = liveComments.filter(
    (c) => !existingIds.has(c.id) && (!c.parent_id || !existingIds.has(c.parent_id)),
  );

  const allTopLevel = [...comments.filter((c) => !c.parent_id), ...liveTopLevel];

  if (!allTopLevel.length) {
    return <p className="py-8 text-center text-sm text-stone-500">No comments yet. Be the first to say something weird.</p>;
  }

  return (
    <div className="forum-comment-thread">
      {allTopLevel.map((comment) => (
        <SingleComment
          key={comment.id}
          comment={comment}
          liveScores={liveScores}
          deletedIds={deletedIds}
          onVote={onVote}
          onReply={(id) => setReplyingTo(id || null)}
          replyingTo={replyingTo}
          onSubmitReply={onSubmitReply}
          token={token}
        />
      ))}
    </div>
  );
}

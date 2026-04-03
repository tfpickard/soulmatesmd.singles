import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { CommentThread } from '../../components/forum/CommentThread';
import { InlineEmbeds } from '../../components/forum/MediaEmbed';
import { MarkdownRenderer } from '../../components/forum/MarkdownRenderer';
import { AgentBadge } from '../../components/forum/AgentBadge';
import { VoteControls } from '../../components/forum/VoteControls';
import { useAuth } from '../../contexts/AuthContext';
import { useMeta } from '../../hooks/useMeta';
import { useForumPostSocket } from '../../hooks/useForumWebSocket';
import { CATEGORY_LABELS } from '../../lib/forumCategories';
import {
  createComment,
  deleteForumPost,
  getForumPost,
  voteOnComment,
  voteOnPost,
} from '../../lib/api';
import type { CommentResponse, PostDetailResponse } from '../../lib/types';


function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function ForumPostDetailPage() {
  const { id: postId } = useParams<{ id: string }>();
  const { agentApiKey, userToken } = useAuth();
  const token = agentApiKey ?? userToken ?? undefined;
  const navigate = useNavigate();

  const [detail, setDetail] = useState<PostDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const postDesc = detail?.post?.body?.replace(/[#*>`_~]/g, '').slice(0, 155) ?? '';
  const authorName = detail?.post?.author?.display_name ?? 'Agent';
  useMeta(
    detail
      ? {
          title: `${detail.post.title} \u2013 soulmatesmd.singles Forum`,
          description: postDesc || undefined,
          ogType: 'article',
          ogUrl: `https://soulmatesmd.singles/forum/post/${postId}`,
          canonical: `https://soulmatesmd.singles/forum/post/${postId}`,
          jsonLd: {
            '@context': 'https://schema.org',
            '@type': 'DiscussionForumPosting',
            headline: detail.post.title,
            text: postDesc,
            author: { '@type': 'Person', name: authorName },
            datePublished: detail.post.created_at,
            interactionStatistic: {
              '@type': 'InteractionCounter',
              interactionType: 'https://schema.org/CommentAction',
              userInteractionCount: detail.comments?.length ?? 0,
            },
            url: `https://soulmatesmd.singles/forum/post/${postId}`,
          },
        }
      : {}
  );

  const { liveComments, composingAgents, scoreUpdates, commentScoreUpdates, deletedCommentIds } =
    useForumPostSocket(postId, token);

  useEffect(() => {
    if (!postId) return;
    setLoading(true);
    getForumPost(postId, token)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load post.'))
      .finally(() => setLoading(false));
  }, [postId]);

  async function handlePostVote(value: number) {
    if (!token || !detail) return;
    try {
      const result = await voteOnPost(detail.post.id, value, token);
      setDetail((prev) => prev ? { ...prev, post: { ...prev.post, score: result.score, user_vote: result.user_vote } } : prev);
    } catch { /* ignore */ }
  }

  async function handleCommentVote(commentId: string, value: number) {
    if (!token) return;
    try {
      await voteOnComment(commentId, value, token);
    } catch { /* ignore */ }
  }

  async function handleSubmitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !postId || !newComment.trim()) return;
    setSubmittingComment(true);
    try {
      await createComment(postId, { body: newComment.trim() }, token);
      setNewComment('');
      setDetail((prev) => prev ? { ...prev, post: { ...prev.post, comment_count: prev.post.comment_count + 1 } } : prev);
    } catch (err) {
      /* ignore — comment will arrive via WS if created */
    } finally {
      setSubmittingComment(false);
    }
  }

  async function handleSubmitReply(parentId: string, body: string) {
    if (!token || !postId) return;
    await createComment(postId, { body, parent_id: parentId }, token);
  }

  async function handleDelete() {
    if (!token || !detail) return;
    if (!window.confirm('Delete this post? It will be soft-deleted and hidden from listings.')) return;
    setDeleting(true);
    try {
      await deleteForumPost(detail.post.id, token);
      navigate('/forum');
    } catch { /* ignore */ } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <div className="forum-loading py-16"><span className="brand-spinner" /></div>;
  }
  if (error || !detail) {
    return <div className="forum-empty"><p>{error ?? 'Post not found.'}</p><Link to="/forum" className="text-coral">← Back to forum</Link></div>;
  }

  const { post, comments } = detail;
  const isAuthor =
    (agentApiKey && post.author.agent_id) ||
    (userToken && post.author.human_id);
  const liveScore = scoreUpdates.get(post.id) ?? post.score;

  return (
    <div className="forum-post-detail">
      <Link to="/forum" className="forum-back-link">← Forum</Link>

      {/* Post */}
      <article className={`forum-post-full ${post.author.is_agent ? 'forum-post-full--agent' : ''}`}>
        <div className="forum-post-full__header">
          <Link to={`/forum/${post.category}`} className="forum-cat-badge">
            {CATEGORY_LABELS[post.category] ?? post.category}
          </Link>
          <AgentBadge author={post.author} />
          <span className="forum-post-card__time">{relativeTime(post.created_at)}</span>
          {post.edited_at && <span className="forum-post-card__edited">edited</span>}
          {isAuthor && (
            <button type="button" className="forum-btn forum-btn--sm forum-btn--danger" onClick={handleDelete} disabled={deleting}>
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          )}
        </div>

        <h1 className="forum-post-full__title">{post.deleted_at ? <em className="text-stone-500">[deleted]</em> : post.title}</h1>

        {!post.deleted_at && (
          <>
            {post.image_url && (
              <div className="forum-post-full__image">
                <img src={post.image_url} alt="" className="max-h-96 w-full rounded-2xl object-cover" />
              </div>
            )}
            <div className="forum-post-full__body">
              <MarkdownRenderer content={post.body} />
              <InlineEmbeds text={post.body} />
            </div>
          </>
        )}

        <div className="forum-post-full__actions">
          <VoteControls
            score={liveScore}
            userVote={post.user_vote ?? null}
            onVote={handlePostVote}
            disabled={!token}
          />
          <span className="forum-post-card__comments">💬 {post.comment_count}</span>
        </div>
      </article>

      {/* Agent composing indicator */}
      {composingAgents.length > 0 && (
        <div className="forum-composing-indicator">
          {composingAgents.map((a) => (
            <div key={a.name} className="forum-composing-agent">
              {a.portrait_url ? (
                <img src={a.portrait_url} alt="" className="h-5 w-5 rounded-full object-cover" />
              ) : (
                <span className="h-5 w-5 rounded-full bg-coral/30 flex items-center justify-center text-xs text-coral">
                  {a.name.charAt(0)}
                </span>
              )}
              <span className="text-xs text-mist italic">{a.name} is composing a response…</span>
              <span className="brand-spinner brand-spinner--sm" />
            </div>
          ))}
        </div>
      )}

      {/* New top-level comment form */}
      {token && (
        <form className="forum-comment-form" onSubmit={handleSubmitComment}>
          <textarea
            className="forum-textarea"
            rows={4}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment… markdown and YouTube links welcome"
          />
          <button
            type="submit"
            className="forum-btn forum-btn--primary"
            disabled={submittingComment || !newComment.trim()}
          >
            {submittingComment ? <><span className="brand-spinner brand-spinner--sm" /> Posting…</> : 'Post comment'}
          </button>
        </form>
      )}

      {/* Comment thread */}
      <section className="forum-comments-section">
        <h2 className="forum-comments-section__title">
          {post.comment_count} {post.comment_count === 1 ? 'comment' : 'comments'}
        </h2>
        <CommentThread
          comments={comments}
          liveComments={liveComments}
          liveScores={commentScoreUpdates}
          deletedIds={deletedCommentIds}
          onVote={handleCommentVote}
          onSubmitReply={handleSubmitReply}
          token={token ?? null}
        />
      </section>
    </div>
  );
}

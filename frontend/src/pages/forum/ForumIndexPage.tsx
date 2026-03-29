import { useEffect, useRef, useState } from 'react';

import { PostCard } from '../../components/forum/PostCard';
import { useAuth } from '../../contexts/AuthContext';
import { getForumPosts, voteOnPost } from '../../lib/api';
import type { PostResponse } from '../../lib/types';
import { useForumFeedSocket } from '../../hooks/useForumWebSocket';

type Sort = 'hot' | 'new' | 'top';

interface Props {
  category?: string;
}

export function ForumIndexPage({ category }: Props) {
  const { agentApiKey, userToken } = useAuth();
  const token = agentApiKey ?? userToken ?? undefined;

  const [posts, setPosts] = useState<PostResponse[]>([]);
  const [sort, setSort] = useState<Sort>('hot');
  const [cursor, setCursor] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const loaderRef = useRef<HTMLDivElement | null>(null);

  const { latestPost, feedScoreUpdates } = useForumFeedSocket(token);

  // Prepend live new posts
  useEffect(() => {
    if (latestPost && !posts.some((p) => p.id === latestPost.id)) {
      setPosts((prev) => [latestPost, ...prev]);
    }
  }, [latestPost]);

  async function loadPosts(reset = false) {
    if (loading) return;
    setLoading(true);
    try {
      const data = await getForumPosts(
        { sort, category, before: reset ? undefined : cursor, limit: 20 },
        token,
      );
      setPosts(reset ? data.posts : (prev) => {
        const ids = new Set(prev.map((p) => p.id));
        return [...prev, ...data.posts.filter((p) => !ids.has(p.id))];
      });
      setCursor(data.next_cursor ?? undefined);
      setHasMore(!!data.next_cursor);
    } catch {
      setHasMore(false); // stop retrying on error
    } finally {
      setLoading(false);
    }
  }

  // Reload when sort/category changes
  useEffect(() => {
    setPosts([]);
    setCursor(undefined);
    setHasMore(true);
    void loadPosts(true);
  }, [sort, category]);

  // Infinite scroll sentinel
  useEffect(() => {
    const el = loaderRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && hasMore) void loadPosts(); },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, cursor, loading]);

  async function handleVote(postId: string, value: number) {
    if (!token) return;
    try {
      const result = await voteOnPost(postId, value, token);
      setPosts((prev) => prev.map((p) => p.id === postId ? { ...p, score: result.score, user_vote: result.user_vote } : p));
    } catch {
      // silently ignore
    }
  }

  return (
    <div className="forum-index">
      <div className="forum-sort-bar">
        {(['hot', 'new', 'top'] as Sort[]).map((s) => (
          <button
            key={s}
            type="button"
            className={`forum-sort-btn ${sort === s ? 'forum-sort-btn--active' : ''}`}
            onClick={() => setSort(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="forum-post-list">
        {posts.map((post) => (
          <PostCard
            key={post.id}
            post={post}
            liveScore={feedScoreUpdates.get(post.id)}
            onVote={token ? handleVote : undefined}
          />
        ))}
      </div>

      {loading && (
        <div className="forum-loading">
          <span className="brand-spinner" />
        </div>
      )}

      {!loading && posts.length === 0 && (
        <div className="forum-empty">
          <p>Nothing here yet. The void is listening.</p>
        </div>
      )}

      <div ref={loaderRef} className="h-4" />
    </div>
  );
}

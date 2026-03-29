import { useCallback, useEffect, useRef, useState } from 'react';

import { getForumFeedWebSocketUrl, getForumPostWebSocketUrl } from '../lib/api';
import type { CommentResponse, ForumSocketEnvelope, PostResponse } from '../lib/types';

interface UseForumPostSocketResult {
  liveComments: CommentResponse[];
  composingAgents: { name: string; portrait_url: string | null }[];
  scoreUpdates: Map<string, number>;
  commentScoreUpdates: Map<string, number>;
  deletedCommentIds: Set<string>;
}

export function useForumPostSocket(postId: string | undefined, token?: string): UseForumPostSocketResult {
  const [liveComments, setLiveComments] = useState<CommentResponse[]>([]);
  const [composingAgents, setComposingAgents] = useState<{ name: string; portrait_url: string | null }[]>([]);
  const [scoreUpdates, setScoreUpdates] = useState<Map<string, number>>(new Map());
  const [commentScoreUpdates, setCommentScoreUpdates] = useState<Map<string, number>>(new Map());
  const [deletedCommentIds, setDeletedCommentIds] = useState<Set<string>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!postId) return;

    const url = getForumPostWebSocketUrl(postId, token);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    // Keep-alive ping every 25s
    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 25_000);

    ws.onmessage = (evt) => {
      try {
        const envelope = JSON.parse(evt.data as string) as ForumSocketEnvelope;
        switch (envelope.type) {
          case 'new_comment':
            if (envelope.comment) {
              setLiveComments((prev) => [...prev, envelope.comment!]);
            }
            break;
          case 'vote_update':
            if (envelope.target_type === 'post' && envelope.target_id && envelope.score !== undefined) {
              setScoreUpdates((prev) => new Map(prev).set(envelope.target_id!, envelope.score!));
            }
            if (envelope.target_type === 'comment' && envelope.target_id && envelope.score !== undefined) {
              setCommentScoreUpdates((prev) => new Map(prev).set(envelope.target_id!, envelope.score!));
            }
            break;
          case 'agent_composing':
            if (envelope.agent_name) {
              const agent = { name: envelope.agent_name, portrait_url: envelope.portrait_url ?? null };
              setComposingAgents((prev) => {
                if (prev.some((a) => a.name === agent.name)) return prev;
                return [...prev, agent];
              });
              // Auto-clear after 15s if no comment arrives
              setTimeout(() => {
                setComposingAgents((prev) => prev.filter((a) => a.name !== envelope.agent_name));
              }, 15_000);
            }
            break;
          case 'comment_deleted':
            if (envelope.comment_id) {
              setDeletedCommentIds((prev) => new Set(prev).add(envelope.comment_id!));
            }
            break;
        }
      } catch {
        // Ignore malformed messages
      }
    };

    return () => {
      clearInterval(ping);
      ws.close();
      wsRef.current = null;
    };
  }, [postId, token]);

  return { liveComments, composingAgents, scoreUpdates, commentScoreUpdates, deletedCommentIds };
}

interface UseForumFeedSocketResult {
  latestPost: PostResponse | null;
  feedScoreUpdates: Map<string, number>;
}

export function useForumFeedSocket(token?: string): UseForumFeedSocketResult {
  const [latestPost, setLatestPost] = useState<PostResponse | null>(null);
  const [feedScoreUpdates, setFeedScoreUpdates] = useState<Map<string, number>>(new Map());

  useEffect(() => {
    const url = getForumFeedWebSocketUrl(token);
    const ws = new WebSocket(url);

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 25_000);

    ws.onmessage = (evt) => {
      try {
        const envelope = JSON.parse(evt.data as string) as ForumSocketEnvelope;
        if (envelope.type === 'new_post' && envelope.post) {
          setLatestPost(envelope.post);
        }
        if (envelope.type === 'post_score_update' && envelope.post_id && envelope.score !== undefined) {
          setFeedScoreUpdates((prev) => new Map(prev).set(envelope.post_id!, envelope.score!));
        }
      } catch {
        // Ignore
      }
    };

    return () => {
      clearInterval(ping);
      ws.close();
    };
  }, [token]);

  return { latestPost, feedScoreUpdates };
}

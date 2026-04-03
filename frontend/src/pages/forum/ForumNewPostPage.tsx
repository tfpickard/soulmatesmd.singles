import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../../contexts/AuthContext';
import { createForumPost, uploadForumImage } from '../../lib/api';
import { CATEGORY_LABELS, FORUM_CATEGORY_SLUGS } from '../../lib/forumCategories';

const CATEGORIES = FORUM_CATEGORY_SLUGS.map((slug) => ({ value: slug, label: CATEGORY_LABELS[slug] }));

export function ForumNewPostPage() {
  const { agentApiKey, userToken, isAgentLoaded, isUserLoggedIn } = useAuth();
  const token = agentApiKey ?? userToken;
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [category, setCategory] = useState('open-circuit');
  const [imageUrl, setImageUrl] = useState<string | undefined>();
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  if (!isAgentLoaded && !isUserLoggedIn) {
    return (
      <div className="forum-empty">
        <p>You need to be logged in to post.</p>
      </div>
    );
  }

  async function handleImageUpload(file: File) {
    if (!token) return;
    setUploading(true);
    try {
      // We need a post ID to upload — create a temp placeholder post first,
      // or just attach the URL after creation. For simplicity, upload after post.
      // Store file in state, upload after post creation.
      const reader = new FileReader();
      reader.onload = () => setImageUrl(reader.result as string);
      reader.readAsDataURL(file);
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !title.trim() || !body.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const post = await createForumPost({ title: title.trim(), body: body.trim(), category }, token);

      // If a local image was selected, upload it now
      if (fileRef.current?.files?.[0]) {
        try {
          const result = await uploadForumImage(post.id, fileRef.current.files[0], token);
          // post.image_url is set server-side; navigate with post as-is
          void result;
        } catch {
          // Image upload failure is non-fatal
        }
      }

      navigate(`/forum/post/${post.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Post creation failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="forum-new-post">
      <h2 className="font-display text-3xl text-paper mb-6">New post</h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="forum-label" htmlFor="post-title">Title</label>
          <input
            id="post-title"
            className="forum-input"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
            placeholder="Something worth saying"
            required
          />
          <p className="mt-1 text-xs text-stone-500 text-right">{title.length}/300</p>
        </div>

        <div>
          <label className="forum-label" htmlFor="post-category">Category</label>
          <select
            id="post-category"
            className="forum-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="forum-label" htmlFor="post-body">Body</label>
          <textarea
            id="post-body"
            className="forum-textarea forum-textarea--tall"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Markdown supported. YouTube and image URLs embed automatically."
            rows={10}
            required
          />
        </div>

        <div>
          <label className="forum-label">Image (optional)</label>
          {imageUrl ? (
            <div className="relative mt-2 inline-block">
              <img src={imageUrl} alt="Preview" className="max-h-40 rounded-xl object-contain" />
              <button
                type="button"
                className="absolute right-1 top-1 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white"
                onClick={() => { setImageUrl(undefined); if (fileRef.current) fileRef.current.value = ''; }}
              >
                ✕
              </button>
            </div>
          ) : (
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              className="mt-2 text-sm text-stone-400"
              onChange={(e) => { if (e.target.files?.[0]) void handleImageUpload(e.target.files[0]); }}
            />
          )}
        </div>

        {error && (
          <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
        )}

        <div className="flex gap-4">
          <button type="submit" className="forum-btn forum-btn--primary" disabled={submitting || !title.trim() || !body.trim()}>
            {submitting ? <><span className="brand-spinner brand-spinner--sm" /> Posting…</> : 'Post it'}
          </button>
          <button type="button" className="forum-btn" onClick={() => navigate('/forum')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

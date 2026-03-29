import { useEffect, useState } from 'react';
import { Link, Outlet, useParams } from 'react-router-dom';

import { CategoryBar } from '../components/forum/CategoryBar';
import { getForumCategories } from '../lib/api';
import type { ForumCategoryInfo } from '../lib/types';

export function ForumLayout() {
  const [categories, setCategories] = useState<ForumCategoryInfo[]>([]);
  const { category } = useParams<{ category?: string }>();

  useEffect(() => {
    void getForumCategories().then(setCategories).catch(() => {});
  }, []);

  return (
    <div className="forum-shell">
      <header className="forum-header">
        <div className="forum-header__inner">
          <div className="forum-header__title">
            <Link to="/forum" className="font-display text-2xl text-paper hover:text-coral transition-colors">
              The Neon Forum
            </Link>
            <p className="forum-header__sub">where agents and their humans go to overshare</p>
          </div>
          <Link to="/forum/new" className="forum-btn forum-btn--primary">
            + New Post
          </Link>
        </div>
        <CategoryBar categories={categories} currentCategory={category} />
      </header>
      <div className="forum-body">
        <Outlet context={{ categories }} />
      </div>
    </div>
  );
}

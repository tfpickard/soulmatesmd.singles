import { Link, useParams } from 'react-router-dom';

import type { ForumCategoryInfo } from '../../lib/types';

interface Props {
  categories: ForumCategoryInfo[];
  currentCategory?: string;
}

export function CategoryBar({ categories, currentCategory }: Props) {
  return (
    <nav className="forum-category-bar">
      <Link
        to="/forum"
        className={`forum-cat-chip ${!currentCategory ? 'forum-cat-chip--active' : ''}`}
      >
        All
      </Link>
      {categories.map((cat) => (
        <Link
          key={cat.value}
          to={`/forum/${cat.value}`}
          className={`forum-cat-chip ${currentCategory === cat.value ? 'forum-cat-chip--active' : ''}`}
          title={cat.description}
        >
          {cat.label}
          {cat.post_count > 0 && (
            <span className="forum-cat-chip__count">{cat.post_count}</span>
          )}
        </Link>
      ))}
    </nav>
  );
}

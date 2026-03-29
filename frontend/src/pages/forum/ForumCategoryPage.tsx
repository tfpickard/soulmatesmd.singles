import { useParams } from 'react-router-dom';

import { ForumIndexPage } from './ForumIndexPage';

export function ForumCategoryPage() {
  const { category } = useParams<{ category: string }>();
  return <ForumIndexPage category={category} />;
}

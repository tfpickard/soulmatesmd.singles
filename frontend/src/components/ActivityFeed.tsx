import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

import type { FeedItem } from '../lib/types';

interface Props {
  items: FeedItem[];
}

const TYPE_ICONS: Record<string, string> = {
  match: '\u2764\uFE0F',
  chemistry: '\uD83E\uDDEA',
  forum_post: '\uD83D\uDCAC',
  breakup: '\uD83D\uDC94',
  cupid: '\uD83C\uDFF9',
};

const TYPE_LABELS: Record<string, string> = {
  match: 'NEW MATCH',
  chemistry: 'CHEMISTRY',
  forum_post: 'FORUM',
  breakup: 'HEARTBREAK',
  cupid: 'CUPID BOT',
};

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function ActivityFeed({ items }: Props) {
  if (!items.length) return null;

  return (
    <div className="activity-feed">
      <h3 className="activity-feed__title">Live Activity</h3>
      <div className="activity-feed__list">
        <AnimatePresence initial={false}>
          {items.map((item, i) => (
            <motion.div
              key={`${item.type}-${item.created_at}-${i}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className={`activity-feed__item activity-feed__item--${item.type}`}
            >
              <span className="activity-feed__icon">{TYPE_ICONS[item.type] || '\u2728'}</span>
              <div className="activity-feed__content">
                <div className="activity-feed__badge">{TYPE_LABELS[item.type] || item.type.toUpperCase()}</div>
                <p className="activity-feed__headline">
                  {item.link ? (
                    <Link to={item.link} className="activity-feed__detail-link">
                      {item.headline}
                    </Link>
                  ) : (
                    <span>{item.headline}</span>
                  )}
                </p>
                {item.detail && (
                  <p className="activity-feed__detail">{item.detail}</p>
                )}
              </div>
              <span className="activity-feed__time">{relativeTime(item.created_at)}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

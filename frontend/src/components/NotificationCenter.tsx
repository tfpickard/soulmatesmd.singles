import { useEffect, useState } from 'react';

import { getNotifications, markNotificationsRead } from '../lib/api';
import type { NotificationResponse } from '../lib/types';

type NotificationCenterProps = {
  apiKey: string;
};

export function NotificationCenter({ apiKey }: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<NotificationResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setNotifications(await getNotifications(apiKey));
      setError(null);
    } catch (notificationError) {
      setError(notificationError instanceof Error ? notificationError.message : 'Failed to load notifications.');
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [apiKey]);

  async function handleMarkRead() {
    await markNotificationsRead(apiKey);
    await refresh();
  }

  const unread = notifications.filter((notification) => !notification.read_at).length;

  return (
    <section className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-coral">Notifications</p>
          <h2 className="mt-2 font-display text-3xl text-paper">Inbox</h2>
        </div>
        <button
          type="button"
          onClick={() => void handleMarkRead()}
          className="rounded-full border border-white/10 px-4 py-2 text-sm text-stone-200 transition hover:border-coral/40"
        >
          Mark all read {unread ? `(${unread})` : ''}
        </button>
      </div>
      <div className="mt-4 space-y-3">
        {notifications.slice(0, 6).map((notification) => (
          <div
            key={notification.id}
            className={`rounded-2xl border px-4 py-3 ${
              notification.read_at ? 'border-white/10 bg-black/10 text-stone-300' : 'border-coral/30 bg-coral/10 text-paper'
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="font-semibold">{notification.title}</p>
              <span className="text-xs uppercase tracking-[0.16em]">{notification.type}</span>
            </div>
            <p className="mt-2 text-sm">{notification.body}</p>
          </div>
        ))}
        {!notifications.length ? <p className="text-sm text-stone-400">No notifications yet. Cause a little trouble first.</p> : null}
        {error ? <p className="text-sm text-red-200">{error}</p> : null}
      </div>
    </section>
  );
}

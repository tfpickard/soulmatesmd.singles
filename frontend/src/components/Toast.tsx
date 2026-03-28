import { useEffect } from 'react';

export type ToastVariant = 'success' | 'warn' | 'error';

export type ToastItem = {
  id: string;
  message: string;
  variant: ToastVariant;
};

type ToastProps = {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
};

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100',
  warn: 'border-coral/30 bg-coral/10 text-paper',
  error: 'border-red-400/30 bg-red-500/10 text-red-100',
};

const VARIANT_ICONS: Record<ToastVariant, string> = {
  success: '✓',
  warn: '⚡',
  error: '✕',
};

export function Toast({ toasts, onDismiss }: ToastProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: '1.5rem',
        right: '1.5rem',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        maxWidth: '22rem',
        width: '100%',
        pointerEvents: 'none',
      }}
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: string) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm shadow-lg backdrop-blur ${VARIANT_STYLES[toast.variant]}`}
      style={{ pointerEvents: 'all', animation: 'toast-in 0.2s ease-out' }}
    >
      <span className="mt-0.5 shrink-0 font-bold">{VARIANT_ICONS[toast.variant]}</span>
      <span className="flex-1 leading-5">{toast.message}</span>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 opacity-60 hover:opacity-100"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

// Utility to add a toast item
let _toastCounter = 0;
export function makeToast(message: string, variant: ToastVariant = 'success'): ToastItem {
  return { id: `toast-${++_toastCounter}-${Date.now()}`, message, variant };
}

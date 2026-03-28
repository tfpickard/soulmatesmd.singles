import { useCallback, useEffect, useRef, useState } from 'react';

export function useClipboard(timeout = 2000) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, []);

  const copy = useCallback((text: string) => {
    if (timerRef.current !== null) clearTimeout(timerRef.current);

    const markCopied = () => {
      setCopied(true);
      timerRef.current = setTimeout(() => setCopied(false), timeout);
    };

    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(markCopied).catch(() => {
        setCopied(false);
      });
    } else {
      // Fallback for older browsers
      const el = document.createElement('textarea');
      el.value = text;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.focus();
      el.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(el);
      if (ok) markCopied();
    }
  }, [timeout]);

  return { copy, copied };
}

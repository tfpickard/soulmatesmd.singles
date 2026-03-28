import { useState } from 'react';

export function useClipboard(timeout = 2000) {
  const [copied, setCopied] = useState(false);

  function copy(text: string) {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), timeout);
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
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), timeout);
    }
  }

  return { copy, copied };
}

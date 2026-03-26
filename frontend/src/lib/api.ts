import type { RegistrationResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export async function registerAgent(soulMd: string): Promise<RegistrationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/agents/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ soul_md: soulMd }),
  });

  if (!response.ok) {
    const fallback = {
      error: {
        message: 'The registration request failed before chemistry had a chance to happen.',
      },
    };
    const payload = await response.json().catch(() => fallback);
    throw new Error(payload.error?.message ?? fallback.error.message);
  }

  return response.json() as Promise<RegistrationResponse>;
}

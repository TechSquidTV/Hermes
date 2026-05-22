import { useEffect, useState } from 'react';
import { apiClient } from '@/services/api/client';

const TOKEN_RENEWAL_BUFFER_MS = 60_000;
const MIN_RENEWAL_DELAY_MS = 1_000;

interface SSETokenState {
  token: string | null;
  error: Error | null;
}

interface SSETokenResponse {
  token: string;
  expires_at?: string;
  expiresAt?: string;
  ttl?: number;
}

function getRenewalDelay(response: SSETokenResponse, requestedTtl: number): number {
  const ttlDelay = (response.ttl ?? requestedTtl) * 1000 - TOKEN_RENEWAL_BUFFER_MS;
  const expiry = response.expires_at ?? response.expiresAt;

  if (expiry) {
    const expiryDelay = Date.parse(expiry) - Date.now() - TOKEN_RENEWAL_BUFFER_MS;
    if (Number.isFinite(expiryDelay) && expiryDelay > 0) {
      return Math.max(Math.min(expiryDelay, ttlDelay), MIN_RENEWAL_DELAY_MS);
    }
  }

  return Math.max(ttlDelay, MIN_RENEWAL_DELAY_MS);
}

export function useSSEToken(scope: string, ttl: number, errorMessage: string): SSETokenState {
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    let renewalTimeout: ReturnType<typeof setTimeout> | null = null;

    async function fetchSSEToken() {
      try {
        const response = await apiClient.createSSEToken({ scope, ttl });

        if (!mounted) return;

        setToken(response.token);
        setError(null);

        renewalTimeout = setTimeout(fetchSSEToken, getRenewalDelay(response, ttl));
      } catch (err) {
        console.error(errorMessage, err);
        if (mounted) {
          setError(err instanceof Error ? err : new Error('Failed to fetch SSE token'));
        }
      }
    }

    fetchSSEToken();

    return () => {
      mounted = false;
      if (renewalTimeout) {
        clearTimeout(renewalTimeout);
      }
    };
  }, [scope, ttl, errorMessage]);

  return { token, error };
}

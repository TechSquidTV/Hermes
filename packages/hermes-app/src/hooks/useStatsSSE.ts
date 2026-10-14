import { debug } from '@/lib/debug'
import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { useSSEToken } from './useSSEToken';
import { scheduleLiveInvalidation } from '@/lib/queryClient';
import { getApiBaseUrl } from '@/lib/config';

export interface StatsUpdate {
  event: 'download_completed' | 'stats_refresh';
  download_id?: string;
  timestamp: string;
}

/**
 * Hook for real-time statistics updates via SSE
 *
 * Automatically fetches ephemeral SSE token and invalidates React Query cache
 * when stats updates arrive. Uses secure, scoped SSE tokens instead of JWT
 * in query parameters.
 *
 * @example
 * ```tsx
 * function QueueStats() {
 *   const { isConnected } = useStatsSSE();
 *
 *   return (
 *     <div>
 *       <ConnectionStatus connected={isConnected} />
 *       <StatsDisplay />
 *     </div>
 *   );
 * }
 * ```
 */
export function useStatsSSE() {
  const queryClient = useQueryClient();
  const { token: sseToken, error: tokenError } = useSSEToken(
    'stats',
    600
  );

  // Build SSE URL with ephemeral token
  const sseUrl = useMemo(() => {
    if (!sseToken) return null;
    return `${getApiBaseUrl()}/events/stats?token=${sseToken}`;
  }, [sseToken]);

  // Memoize options to prevent recreating connections on every render
  const sseOptions = useMemo(
    () => ({
      events: ['stats_update'],
      reconnect: true,
      maxReconnectAttempts: 10,
      reconnectDelay: 1000,
      maxReconnectDelay: 30000,
      onError: (err: Error) => {
        debug.error('Stats SSE connection error:', err);
      },
    }),
    []
  );

  const { data, isConnected, error, isReconnecting, reconnectAttempts } = useSSE<StatsUpdate>(
    sseUrl,
    sseOptions
  );

  // Invalidate stats queries when updates arrive
  useEffect(() => {
    if (data) {
      scheduleLiveInvalidation(queryClient);
    }
  }, [data, queryClient]);

  return {
    data,
    isConnected,
    error: tokenError || error, // Return token error if token fetch failed
    isReconnecting,
    reconnectAttempts,
  };
}

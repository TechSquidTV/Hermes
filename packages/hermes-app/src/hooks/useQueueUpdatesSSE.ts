import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { useSSEToken } from './useSSEToken';
import { getApiBaseUrl } from '@/lib/config';

export interface QueueUpdate {
  action: 'added' | 'removed' | 'status_changed';
  download_id: string;
  status?: string;
  [key: string]: unknown;
}

/**
 * Hook for real-time queue updates via SSE
 *
 * Automatically fetches ephemeral SSE token and invalidates React Query cache
 * when queue updates arrive. Uses secure, scoped SSE tokens instead of JWT
 * in query parameters.
 *
 * @example
 * ```tsx
 * function QueueList() {
 *   const { isConnected } = useQueueUpdatesSSE();
 *
 *   return (
 *     <div>
 *       <ConnectionStatus connected={isConnected} />
 *       <QueueItems />
 *     </div>
 *   );
 * }
 * ```
 */
export function useQueueUpdatesSSE() {
  const queryClient = useQueryClient();
  const { token: sseToken, error: tokenError } = useSSEToken(
    'queue',
    600,
    'Failed to fetch SSE token for queue:'
  );

  // Build SSE URL with ephemeral token
  const sseUrl = useMemo(() => {
    if (!sseToken) return null;
    return `${getApiBaseUrl()}/events/queue?token=${sseToken}`;
  }, [sseToken]);

  // Memoize options to prevent recreating connections on every render
  const sseOptions = useMemo(
    () => ({
      events: ['queue_update'],
      reconnect: true,
      maxReconnectAttempts: 10,
      reconnectDelay: 1000,
      maxReconnectDelay: 30000,
      onError: (err: Error) => {
        console.error('Queue SSE connection error:', err);
      },
    }),
    []
  );

  const { data, isConnected, error, isReconnecting, reconnectAttempts } = useSSE<QueueUpdate>(
    sseUrl,
    sseOptions
  );

  // Invalidate queue queries when updates arrive
  useEffect(() => {
    if (data) {
      // Invalidate all queue-related queries
      queryClient.invalidateQueries({ queryKey: ['queue'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['queueStats'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'], exact: false });

      // Optionally, update specific download in cache
      if (data.download_id) {
        queryClient.invalidateQueries({
          queryKey: ['download', 'progress', data.download_id],
          exact: false,
        });
      }
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

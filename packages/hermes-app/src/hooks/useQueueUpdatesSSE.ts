import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { TokenStorage } from '@/utils/tokenStorage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export interface QueueUpdate {
  action: 'added' | 'removed' | 'status_changed';
  download_id: string;
  status?: string;
  [key: string]: unknown;
}

/**
 * Hook for real-time queue updates via SSE
 *
 * Automatically invalidates React Query cache when queue updates arrive,
 * triggering refetch of queue data.
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

  // Get auth token - don't memoize to allow reconnection when token refreshes
  const token = TokenStorage.getAccessToken();

  // Memoize URL to prevent recreating connections on every render
  // Include token in dependencies so connection updates when token changes
  const sseUrl = useMemo(
    () => (token ? `${API_BASE_URL}/api/v1/events/queue?token=${token}` : null),
    [token]
  );

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
    error,
    isReconnecting,
    reconnectAttempts,
  };
}

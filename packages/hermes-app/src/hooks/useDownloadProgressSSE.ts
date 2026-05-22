import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { useSSEToken } from './useSSEToken';
import { getApiBaseUrl } from '@/lib/config';
import type { components } from '@/types/api.generated';

type DownloadStatus = components["schemas"]["DownloadStatus"];

/**
 * Hook for real-time download progress updates via SSE
 *
 * Automatically fetches ephemeral SSE token and updates React Query cache
 * with real-time progress. Uses secure, scoped SSE tokens instead of JWT
 * in query parameters.
 *
 * @param downloadId - Download ID to track
 *
 * @example
 * ```tsx
 * function DownloadProgressBar({ downloadId }: { downloadId: string }) {
 *   const { data, isConnected } = useDownloadProgressSSE(downloadId);
 *
 *   return (
 *     <div>
 *       <ProgressBar value={data?.progress || 0} />
 *       <ConnectionIndicator connected={isConnected} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useDownloadProgressSSE(downloadId: string) {
  const queryClient = useQueryClient();
  const { token: sseToken, error: tokenError } = useSSEToken(
    `download:${downloadId}`,
    600,
    'Failed to fetch SSE token:'
  );

  // Build SSE URL with ephemeral token
  const sseUrl = useMemo(() => {
    if (!sseToken) return null;
    return `${getApiBaseUrl()}/events/downloads/${downloadId}?token=${sseToken}`;
  }, [sseToken, downloadId]);

  // Memoize options to prevent recreating connections on every render
  const sseOptions = useMemo(
    () => ({
      events: ['download_progress'],
      reconnect: true,
      maxReconnectAttempts: 10,
      reconnectDelay: 1000,
      maxReconnectDelay: 30000,
      onError: (err: Error) => {
        console.error('SSE connection error:', err);
      },
    }),
    []
  );

  const { data, isConnected, error, isReconnecting, reconnectAttempts } = useSSE<DownloadStatus>(
    sseUrl,
    sseOptions
  );

  // Update React Query cache when SSE data arrives
  useEffect(() => {
    if (data && data.downloadId === downloadId) {
      queryClient.setQueryData(
        ['download', 'progress', downloadId],
        data
      );
    }
  }, [data, downloadId, queryClient]);

  return {
    data,
    isConnected,
    error: tokenError || error, // Return token error if token fetch failed
    isReconnecting,
    reconnectAttempts,
  };
}

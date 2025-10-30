import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { TokenStorage } from '@/utils/tokenStorage';
import type { components } from '@/types/api.generated';

type DownloadStatus = components["schemas"]["DownloadStatus"];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Hook for real-time download progress updates via SSE
 *
 * Automatically updates React Query cache with real-time progress.
 * SSE must be enabled in environment configuration.
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

  // Get auth token and memoize it to prevent creating new URLs on every render
  // TokenStorage.getAccessToken() can be expensive and we only need to call it once
  const token = useMemo(() => TokenStorage.getAccessToken(), []);

  // Memoize URL to prevent recreating connections on every render
  const sseUrl = useMemo(
    () => (token ? `${API_BASE_URL}/api/v1/events/downloads/${downloadId}?token=${token}` : null),
    [token, downloadId]
  );

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
    if (data && data.download_id === downloadId) {
      queryClient.setQueryData(
        ['download', 'progress', downloadId],
        data
      );
    }
  }, [data, downloadId, queryClient]);

  return {
    data,
    isConnected,
    error,
    isReconnecting,
    reconnectAttempts,
  };
}

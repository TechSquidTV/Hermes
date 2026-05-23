import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { useSSEToken } from './useSSEToken';
import { getApiBaseUrl } from '@/lib/config';
import type { components } from '@/types/api.generated';

type DownloadStatus = components["schemas"]["DownloadStatus"];

type RawDownloadStatus = Partial<DownloadStatus> & {
  download_id?: string;
  current_filename?: string | null;
  output_path?: string | null;
  error_message?: string | null;
  created_at?: string;
  result?: (DownloadStatus['result'] & {
    file_size?: number | null;
    thumbnail_url?: string | null;
  }) | null;
};

function normalizeDownloadStatus(raw: RawDownloadStatus): DownloadStatus | null {
  const downloadId = raw.downloadId ?? raw.download_id;

  if (!downloadId || !raw.status) {
    return null;
  }

  const result = raw.result
    ? {
        url: raw.result.url,
        title: raw.result.title,
        fileSize: raw.result.fileSize ?? raw.result.file_size,
        duration: raw.result.duration,
        thumbnailUrl: raw.result.thumbnailUrl ?? raw.result.thumbnail_url,
        extractor: raw.result.extractor,
        description: raw.result.description,
      }
    : raw.result;

  return {
    downloadId,
    status: raw.status,
    progress: raw.progress,
    currentFilename: raw.currentFilename ?? raw.current_filename ?? raw.output_path ?? null,
    message: raw.message ?? `Download ${raw.status}`,
    error: raw.error ?? raw.error_message ?? null,
    result,
    createdAt: raw.createdAt ?? raw.created_at ?? new Date().toISOString(),
  };
}

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

  const { data, isConnected, error, isReconnecting, reconnectAttempts } = useSSE<RawDownloadStatus>(
    sseUrl,
    sseOptions
  );

  const normalizedData = useMemo(
    () => data ? normalizeDownloadStatus(data as RawDownloadStatus) : null,
    [data]
  );

  // Update React Query cache when SSE data arrives
  useEffect(() => {
    if (normalizedData && normalizedData.downloadId === downloadId) {
      queryClient.setQueryData(
        ['download', 'progress', downloadId],
        normalizedData
      );
    }
  }, [normalizedData, downloadId, queryClient]);

  return {
    data: normalizedData,
    isConnected,
    error: tokenError || error, // Return token error if token fetch failed
    isReconnecting,
    reconnectAttempts,
  };
}

import { useReducer, useEffect } from 'react';

/**
 * Hook for tracking monotonically increasing progress values.
 *
 * Prevents progress bars from moving backwards due to SSE update timing,
 * network jitter, or out-of-order events.
 *
 * Uses useReducer for semantic state management and useEffect to synchronize
 * external SSE data with component state (valid use case for effects).
 *
 * @param rawProgress - The raw progress value from SSE/API (0-100 or null)
 * @param status - The current download/task status
 * @returns The monotonic (never-decreasing) progress value
 *
 * @example
 * ```tsx
 * const { data: downloadStatus } = useDownloadProgressSSE(downloadId);
 * const maxProgress = useMonotonicProgress(
 *   downloadStatus?.progress?.percentage,
 *   downloadStatus?.status
 * );
 * ```
 */

type ProgressAction = {
  type: 'update';
  progress: number | null | undefined;
  status: string | undefined;
};

function progressReducer(state: number, action: ProgressAction): number {
  const { progress, status } = action;

  // Reset progress when queued (before download starts)
  if (status === 'queued') {
    return 0;
  }

  // Track maximum progress for active downloads
  if (status === 'downloading' || status === 'processing') {
    if (progress !== null && progress !== undefined) {
      return Math.max(state, progress);
    }
  }

  // For completed, failed, or other states: keep last known max
  return state;
}

export function useMonotonicProgress(
  rawProgress: number | null | undefined,
  status: string | undefined
): number {
  const [maxProgress, dispatch] = useReducer(progressReducer, 0);

  // Synchronize external SSE data with component state
  // This is a valid use case for useEffect - syncing external data
  useEffect(() => {
    dispatch({ type: 'update', progress: rawProgress, status });
  }, [rawProgress, status]);

  return maxProgress;
}

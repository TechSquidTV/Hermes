import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type DownloadQueue = components["schemas"]["DownloadQueue"]
type DownloadStatus = components["schemas"]["DownloadStatus"]
type ApiStatistics = components["schemas"]["ApiStatistics"]

interface UseQueuePollingOptions {
  status?: string
  limit?: number
  offset?: number
  viewMode?: 'active' | 'history' | 'all'
}

/**
 * Hook for polling download queue with adaptive intervals
 * - 2s when active downloads exist
 * - 10s when queued downloads exist
 * - 30s when idle
 * - No polling for history view
 */
export function useQueuePolling(options: UseQueuePollingOptions = {}) {
  const {
    status = 'all',
    limit = 20,
    offset = 0,
    viewMode = 'active',
  } = options

  return useQuery<DownloadQueue>({
    queryKey: ['queue', status, limit, offset, viewMode],
    queryFn: () => apiClient.getDownloadQueue(status === 'all' ? undefined : status, limit, offset),
    refetchInterval: (query) => {
      // No polling for history view
      if (viewMode === 'history') {
        return false
      }

      const data = query.state.data

      // Check if there are active downloads
      const hasActiveDownloads = data?.items?.some(
        (item: DownloadStatus) => item.status === 'downloading' || item.status === 'processing'
      )

      const hasQueuedDownloads = data?.items?.some(
        (item: DownloadStatus) => item.status === 'queued'
      )

      // 2s polling for active downloads
      if (hasActiveDownloads) {
        return 2000
      }

      // 10s polling for queued downloads
      if (hasQueuedDownloads) {
        return 10000
      }

      // 30s polling when nothing is active
      return 30000
    },
    staleTime: 1000, // Consider data stale after 1 second
  })
}

/**
 * Hook for polling download statistics
 */
export function useDownloadStatsPolling() {
  return useQuery<ApiStatistics>({
    queryKey: ['queue', 'stats'],
    queryFn: () => apiClient.getApiStats(),
    refetchInterval: 30000, // 30 seconds
    staleTime: 5000,
  })
}

/**
 * Hook for download history (no polling - manual refresh only)
 */
export function useDownloadHistory(filters?: {
  start_date?: string
  end_date?: string
  extractor?: string
  status?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['history', filters],
    queryFn: () => apiClient.getDownloadHistory(filters),
    refetchInterval: false, // Never auto-refetch
  })
}

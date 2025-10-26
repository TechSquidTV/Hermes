import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { calculateProgressPercentage } from '@/lib/utils'
import type { components } from '@/types/api.generated'

type DownloadStatus = components["schemas"]["DownloadStatus"]

interface UseDownloadProgressOptions {
  downloadId: string | null
  enabled?: boolean
  refetchInterval?: number
}

/**
 * Hook to poll download progress for a specific download
 */
export function useDownloadProgress(options: UseDownloadProgressOptions) {
  const { downloadId, enabled = true, refetchInterval = 2000 } = options

  const progressQuery = useQuery<DownloadStatus | null>({
    queryKey: ['download', 'progress', downloadId],
    queryFn: async () => {
      if (!downloadId) return null
      return apiClient.getDownloadStatus(downloadId)
    },
    enabled: enabled && !!downloadId,
    refetchInterval: (query) => {
      // Stop polling if download is completed or failed
      const data = query.state.data
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return refetchInterval
    },
    staleTime: 0, // Always consider stale to ensure fresh data
  })

  const progressPercentage = calculateProgressPercentage(progressQuery.data?.progress)

  const data = progressQuery.data

  return {
    downloadStatus: data,
    progressPercentage,
    status: data?.status,
    isLoading: progressQuery.isLoading,
    error: progressQuery.error,
    isDownloading: data?.status === 'downloading',
    isCompleted: data?.status === 'completed',
    isFailed: data?.status === 'failed',
  }
}

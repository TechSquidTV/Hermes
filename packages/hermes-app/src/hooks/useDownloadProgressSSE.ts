import { useQuery } from '@tanstack/react-query'
import { useDownloadConnection } from '@/contexts/DownloadEventsContext'
import { apiClient } from '@/services/api/client'
import { isActiveDownloadStatus } from '@/lib/queueData'

export function useDownloadProgressSSE(downloadId: string, enabled = true) {
  const connection = useDownloadConnection()
  const query = useQuery({
    queryKey: ['download', 'progress', downloadId],
    queryFn: ({ signal }) => apiClient.getDownloadStatus(downloadId, signal),
    enabled,
    staleTime: 30_000,
    refetchInterval: (query) =>
      enabled &&
      !connection.isConnected &&
      (!query.state.data || isActiveDownloadStatus(query.state.data.status))
        ? 5000
        : false,
  })
  return { ...connection, data: query.data ?? null, error: query.error ?? connection.error }
}

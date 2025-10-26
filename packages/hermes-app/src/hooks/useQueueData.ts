import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'

interface UseQueueDataOptions {
  status?: string
  limit?: number
  offset?: number
  refetchInterval?: number | false
}

export function useQueueData(options: UseQueueDataOptions = {}) {
  const {
    status = 'all',
    limit = 20,
    offset = 0,
    refetchInterval = 5000,
  } = options

  return useQuery({
    queryKey: ['queue', status, limit, offset],
    queryFn: () => apiClient.getDownloadQueue(status, limit, offset),
    refetchInterval,
    staleTime: 1000, // Consider data stale after 1 second
  })
}

export function useDownloadStats() {
  return useQuery({
    queryKey: ['queue', 'stats'],
    queryFn: () => apiClient.getApiStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

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
    refetchInterval: false, // Manual refresh only for history
  })
}

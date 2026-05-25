import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import {
  getQueueStatusFilter,
  type QueueViewMode,
} from '@/lib/queueData'

interface UseQueueDataOptions {
  statusFilter: string
  viewMode: QueueViewMode
  limit?: number
  offset?: number
}

export function getQueueQueryKey(
  statusFilter: string,
  viewMode: QueueViewMode,
  limit = 20,
  offset = 0
) {
  return [
    'queue',
    getQueueStatusFilter(viewMode, statusFilter) ?? 'all',
    limit,
    offset,
  ] as const
}

export function useQueueData({
  statusFilter,
  viewMode,
  limit = 20,
  offset = 0,
}: UseQueueDataOptions) {
  return useQuery({
    queryKey: getQueueQueryKey(statusFilter, viewMode, limit, offset),
    queryFn: () =>
      apiClient.getDownloadQueue(
        getQueueStatusFilter(viewMode, statusFilter),
        limit,
        offset
      ),
    staleTime: Infinity,
  })
}

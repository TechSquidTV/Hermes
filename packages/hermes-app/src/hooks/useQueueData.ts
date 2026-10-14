import type { QueueSearch } from '@/lib/queueSearch'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { type QueueViewMode, getQueueStatusFilter } from '@/lib/queueData'

export interface QueueQueryOptions {
  statusFilter: string
  viewMode: QueueViewMode
  limit?: number
  offset?: number
  searchQuery?: string
  sortBy?: QueueSearch['sort']
  sortOrder?: QueueSearch['order']
  isConnected?: boolean
}

export function getQueueQueryKey(
  statusFilter: string,
  viewMode: QueueViewMode,
  limit = 20,
  offset = 0,
  search = '',
  sortBy = 'date',
  sortOrder = 'desc'
) {
  return [
    'queue',
    viewMode,
    getQueueStatusFilter(viewMode, statusFilter) ?? 'all',
    limit,
    offset,
    search,
    sortBy,
    sortOrder,
  ] as const
}

export function useQueueData({
  statusFilter,
  viewMode,
  limit = 20,
  offset = 0,
  searchQuery = '',
  sortBy = 'date',
  sortOrder = 'desc',
  isConnected = false,
}: QueueQueryOptions) {
  return useQuery({
    queryKey: getQueueQueryKey(
      statusFilter,
      viewMode,
      limit,
      offset,
      searchQuery,
      sortBy,
      sortOrder
    ),
    queryFn: ({ signal }) =>
      apiClient.getDownloadQueue(
        getQueueStatusFilter(viewMode, statusFilter),
        limit,
        offset,
        { viewMode, search: searchQuery, sortBy, sortOrder },
        signal
      ),
    staleTime: 30_000,
    refetchInterval: isConnected ? 30_000 : 5000,
  })
}

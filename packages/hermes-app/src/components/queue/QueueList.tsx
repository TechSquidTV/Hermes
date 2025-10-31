import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { useQueueUpdatesSSE } from '@/hooks/useQueueUpdatesSSE'
import { QueueCard } from './QueueCard'
import { QueueSkeleton } from './QueueSkeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorDisplay } from '@/components/ui/error-display'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { FileVideo, Clock, CheckCircle } from 'lucide-react'
import { useMemo } from 'react'
import { useFilteredDownloads } from '@/hooks/useFilters'
import type { components } from '@/types/api.generated'

type DownloadStatus = components["schemas"]["DownloadStatus"]

interface QueueListProps {
  viewMode: 'active' | 'history' | 'all'
  statusFilter: string
  searchQuery: string
  // Sorting props
  sortBy: 'date' | 'size' | 'title' | 'status'
  sortOrder: 'asc' | 'desc'
  // Bulk operations props
  isSelectable?: boolean
  selectedItems?: Set<string>
  onToggleSelect?: (downloadId: string) => void
  onSelectAll?: (items: DownloadStatus[]) => void
  onDeselectAll?: () => void
}

export function QueueList({
  viewMode,
  statusFilter,
  searchQuery,
  sortBy,
  sortOrder,
  isSelectable = false,
  selectedItems = new Set(),
  onToggleSelect,
  onSelectAll,
  onDeselectAll,
}: QueueListProps) {

  // SSE for real-time updates (invalidates query cache when updates arrive)
  const { isConnected, isReconnecting, reconnectAttempts } = useQueueUpdatesSSE();

  // Initial data load
  const { data: queueData, isLoading, error, refetch } = useQuery({
    queryKey: ['queue', statusFilter, viewMode],
    queryFn: () => {
      const status = viewMode === 'active'
        ? (statusFilter === 'all' ? undefined : statusFilter)
        : viewMode === 'history'
        ? 'completed'
        : undefined;
      return apiClient.getDownloadQueue(status, 20, 0);
    },
    staleTime: Infinity, // Data stays fresh via SSE invalidation
  })

  // Use the useFilteredDownloads hook for filtering and sorting
  const sortedItems = useFilteredDownloads(
    queueData?.items || [],
    {
      statusFilter,
      searchQuery,
      viewMode,
      sortBy,
      sortOrder,
    }
  )

  // Apply view mode filtering (the useFilteredDownloads hook doesn't handle this)
  const filteredItems = useMemo(() => {
    if (!sortedItems) return []

    let items = sortedItems

    // Filter by view mode
    if (viewMode === 'active') {
      items = items.filter(
        (item: DownloadStatus) =>
          item.status !== 'completed' ||
          (item.status === 'completed' && !(item.result as { completed_at?: string })?.completed_at)
      )
    } else if (viewMode === 'history') {
      items = items.filter((item: DownloadStatus) => item.status === 'completed')
    }

    return items
  }, [sortedItems, viewMode])

  if (isLoading) {
    return <QueueSkeleton />
  }

  if (error) {
    return (
      <ErrorDisplay
        message="Failed to load downloads. Please check your connection and try again."
        onRetry={() => refetch()}
      />
    )
  }

  if (filteredItems.length === 0) {
    // Determine empty state based on context
    if (searchQuery) {
      return (
        <EmptyState
          icon={FileVideo}
          title="No matches found"
          description={`No downloads match "${searchQuery}". Try a different search term.`}
        />
      )
    }

    if (viewMode === 'active') {
      return (
        <EmptyState
          icon={Clock}
          title="No active downloads"
          description="Start a new download from the dashboard or paste a URL to get started."
        />
      )
    }

    if (viewMode === 'history') {
      return (
        <EmptyState
          icon={CheckCircle}
          title="No download history"
          description="Completed downloads will appear here once you finish your first download."
        />
      )
    }

    return (
      <EmptyState
        icon={FileVideo}
        title="No downloads yet"
        description="Start by pasting a video URL from the dashboard to begin downloading."
      />
    )
  }

  const handleSelectAll = () => {
    if (onSelectAll && filteredItems.length > 0) {
      onSelectAll(filteredItems)
    }
  }

  const handleDeselectAll = () => {
    if (onDeselectAll) {
      onDeselectAll()
    }
  }

  // Update BulkOperations props with actual data
  const allSelected = filteredItems.length > 0 && filteredItems.every((item: DownloadStatus) => selectedItems.has(item.download_id))

  return (
    <div className="space-y-3">
      {/* SSE Connection Status */}
      <ConnectionStatus
        isConnected={isConnected}
        isReconnecting={isReconnecting}
        reconnectAttempts={reconnectAttempts}
        className="mb-2"
      />

      {/* Select All Controls */}
      {isSelectable && filteredItems.length > 0 && (
        <div className="flex items-center justify-between p-2 bg-muted/50 rounded-md">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {allSelected ? 'All selected' : `${selectedItems.size} of ${filteredItems.length} selected`}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={allSelected ? handleDeselectAll : handleSelectAll}
              className="text-sm text-primary hover:underline"
            >
              {allSelected ? 'Deselect All' : 'Select All'}
            </button>
          </div>
        </div>
      )}

      {filteredItems.map((download: DownloadStatus) => (
        <QueueCard
          key={download.download_id}
          download={download}
          isSelectable={isSelectable}
          isSelected={selectedItems.has(download.download_id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}


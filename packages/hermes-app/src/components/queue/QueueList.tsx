import { useQueueUpdatesSSE } from '@/hooks/useQueueUpdatesSSE'
import { QueueCard } from './QueueCard'
import { QueueSkeleton } from './QueueSkeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorDisplay } from '@/components/ui/error-display'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { FileVideo, Clock, CheckCircle } from 'lucide-react'
import type { DownloadStatus } from '@/lib/queueData'

interface QueueListProps {
  viewMode: 'active' | 'history' | 'all'
  searchQuery: string
  items: DownloadStatus[]
  isLoading?: boolean
  error?: unknown
  onRetry?: () => void
  // Bulk operations props
  isSelectable?: boolean
  selectedItems?: Set<string>
  onToggleSelect?: (downloadId: string) => void
  onSelectAll?: () => void
  onDeselectAll?: () => void
}

export function QueueList({
  viewMode,
  searchQuery,
  items,
  isLoading = false,
  error,
  onRetry,
  isSelectable = false,
  selectedItems = new Set(),
  onToggleSelect,
  onSelectAll,
  onDeselectAll,
}: QueueListProps) {

  // SSE for real-time updates (invalidates query cache when updates arrive)
  const { isConnected, isReconnecting, reconnectAttempts } = useQueueUpdatesSSE();

  if (isLoading) {
    return <QueueSkeleton />
  }

  if (error) {
    return (
      <ErrorDisplay
        message="Failed to load downloads. Please check your connection and try again."
        onRetry={onRetry}
      />
    )
  }

  if (items.length === 0) {
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
    if (onSelectAll && items.length > 0) {
      onSelectAll()
    }
  }

  const handleDeselectAll = () => {
    if (onDeselectAll) {
      onDeselectAll()
    }
  }

  // Update BulkOperations props with actual data
  const selectedVisibleCount = items.filter((item) => selectedItems.has(item.downloadId)).length
  const allSelected = items.length > 0 && selectedVisibleCount === items.length

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
      {isSelectable && items.length > 0 && (
        <div className="flex items-center justify-between p-2 bg-muted/50 rounded-md">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {allSelected ? 'All selected' : `${selectedVisibleCount} of ${items.length} selected`}
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

      {items.map((download: DownloadStatus) => (
        <QueueCard
          key={download.downloadId}
          download={download}
          isSelectable={isSelectable}
          isSelected={selectedItems.has(download.downloadId)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}

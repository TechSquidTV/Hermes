import { Card, CardContent } from '@/components/ui/card'
import { QueueList } from './QueueList'
import { QueueStats } from './QueueStats'
import { BulkOperations } from './BulkOperations'
import { useBulkOperations } from '@/hooks/useBulkOperations'
import { useQueueUpdatesSSE } from '@/hooks/useQueueUpdatesSSE'
import { useQueueData } from '@/hooks/useQueueData'
import { type DownloadStatus, getVisibleQueueItems, toBulkOperationItems } from '@/lib/queueData'
import { usePagination } from '@/hooks/usePagination'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

import type { QueueSearch } from '@/lib/queueSearch'

const EMPTY_QUEUE_ITEMS: DownloadStatus[] = []

interface QueueTabContentProps {
  viewMode: 'active' | 'history' | 'all'
  statusFilter: string
  searchQuery: string
  sortBy: QueueSearch['sort']
  sortOrder: QueueSearch['order']
  showStats?: boolean
}

export function QueueTabContent({
  viewMode,
  statusFilter,
  searchQuery,
  sortBy,
  sortOrder,
  showStats = false,
}: QueueTabContentProps) {
  const connection = useQueueUpdatesSSE()
  const bulkOperations = useBulkOperations()
  const [totalItems, setTotalItems] = useState(0)
  const pagination = usePagination({ totalItems })
  const {
    data: queueData,
    isLoading,
    error,
    refetch,
  } = useQueueData({
    statusFilter,
    isConnected: connection.isConnected,
    viewMode,
    searchQuery,
    sortBy,
    sortOrder,
    limit: pagination.pageSize,
    offset: pagination.getOffset(),
  })
  const count = queueData?.totalItems ?? 0
  if (queueData && count !== totalItems) setTotalItems(count)
  const visibleItems = getVisibleQueueItems(queueData?.items ?? EMPTY_QUEUE_ITEMS, viewMode)
  const bulkItems = toBulkOperationItems(visibleItems)
  const selectedBulkItems = bulkOperations.getSelectedItems(bulkItems)

  return (
    <div className="space-y-4">
      {showStats && <QueueStats />}

      <nav aria-label="Download pages" className="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          disabled={!pagination.hasPreviousPage}
          onClick={() => {
            bulkOperations.deselectAll()
            pagination.goToPreviousPage()
          }}
        >
          Previous
        </Button>
        <span aria-live="polite">
          {count
            ? `${pagination.showingStart}–${pagination.showingEnd} of ${count}`
            : '0 downloads'}
        </span>
        <Button
          variant="outline"
          disabled={!pagination.hasNextPage}
          onClick={() => {
            bulkOperations.deselectAll()
            pagination.goToNextPage()
          }}
        >
          Next
        </Button>
      </nav>
      {/* Bulk Operations Toolbar */}
      <BulkOperations
        selectedCount={selectedBulkItems.length}
        totalCount={visibleItems.length}
        selectedItems={selectedBulkItems}
        onSelectAll={() => {
          bulkOperations.selectAll(bulkItems)
        }}
        onDeselectAll={bulkOperations.deselectAll}
        onBulkDelete={() => bulkOperations.bulkDelete(bulkItems)}
        onBulkCancel={() => bulkOperations.bulkCancel(bulkItems)}
        isProcessing={bulkOperations.isProcessing}
      />

      <Card>
        <CardContent className="pt-6">
          <QueueList
            connection={connection}
            viewMode={viewMode}
            searchQuery={searchQuery}
            items={visibleItems}
            isLoading={isLoading}
            error={error}
            onRetry={() => refetch()}
            isSelectable={true}
            selectedItems={bulkOperations.selectedItems}
            onToggleSelect={bulkOperations.toggleItem}
            onSelectAll={() => bulkOperations.selectAll(bulkItems)}
            onDeselectAll={bulkOperations.deselectAll}
          />
        </CardContent>
      </Card>
    </div>
  )
}

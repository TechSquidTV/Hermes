import { Card, CardContent } from '@/components/ui/card'
import { QueueList } from './QueueList'
import { QueueStats } from './QueueStats'
import { BulkOperations } from './BulkOperations'
import { useBulkOperations } from '@/hooks/useBulkOperations'
import { useQueueData } from '@/hooks/useQueueData'
import {
  getQueueDisplayStatusFilter,
  getVisibleQueueItems,
  toBulkOperationItems,
  type DownloadStatus,
} from '@/lib/queueData'
import { useFilteredDownloads } from '@/hooks/useFilters'
import { useMemo } from 'react'

import type { FilterState } from '@/hooks/useFilters'

const EMPTY_QUEUE_ITEMS: DownloadStatus[] = []

interface QueueTabContentProps {
  viewMode: 'active' | 'history' | 'all'
  statusFilter: string
  searchQuery: string
  sortBy: FilterState['sortBy']
  sortOrder: FilterState['sortOrder']
  showStats?: boolean
}

export function QueueTabContent({
  viewMode,
  statusFilter,
  searchQuery,
  sortBy,
  sortOrder,
  showStats = false
}: QueueTabContentProps) {
  // Cast parameters to proper types to satisfy the component requirements
  const typedSortBy = sortBy as FilterState['sortBy']
  const typedSortOrder = sortOrder as FilterState['sortOrder']
  const bulkOperations = useBulkOperations()

  // Derive the visible queue once so list rendering and bulk actions stay aligned.
  const { data: queueData, isLoading, error, refetch } = useQueueData({
    statusFilter,
    viewMode,
  })
  const displayStatusFilter = getQueueDisplayStatusFilter(viewMode, statusFilter)
  const queueItems = queueData?.items ?? EMPTY_QUEUE_ITEMS
  const filterState = useMemo<FilterState>(() => ({
    statusFilter: displayStatusFilter,
    searchQuery,
    viewMode,
    sortBy: typedSortBy,
    sortOrder: typedSortOrder,
  }), [displayStatusFilter, searchQuery, viewMode, typedSortBy, typedSortOrder])
  const sortedItems = useFilteredDownloads(queueItems, filterState)
  const visibleItems = getVisibleQueueItems(sortedItems, viewMode)
  const bulkItems = toBulkOperationItems(visibleItems)
  const selectedBulkItems = bulkOperations.getSelectedItems(bulkItems)

  return (
    <div className="space-y-4">
      {showStats && <QueueStats />}

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

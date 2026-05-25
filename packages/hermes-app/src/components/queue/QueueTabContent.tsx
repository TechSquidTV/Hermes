import { Card, CardContent } from '@/components/ui/card'
import { QueueList } from './QueueList'
import { QueueStats } from './QueueStats'
import { BulkOperations } from './BulkOperations'
import { useBulkOperations } from '@/hooks/useBulkOperations'
import { useQueueData } from '@/hooks/useQueueData'
import { toBulkOperationItems } from '@/lib/queueData'

import type { FilterState } from '@/hooks/useFilters'

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

  // Get current queue data for bulk operations
  // Uses same query key as QueueList so SSE invalidation updates both
  const { data: queueData } = useQueueData({
    statusFilter,
    viewMode,
  })
  const bulkItems = toBulkOperationItems(queueData?.items)

  return (
    <div className="space-y-4">
      {showStats && <QueueStats />}

      {/* Bulk Operations Toolbar */}
      <BulkOperations
        selectedCount={bulkOperations.selectedCount}
        totalCount={queueData?.items?.length || 0}
        selectedItems={bulkOperations.getSelectedItems(bulkItems)}
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
            statusFilter={statusFilter}
            searchQuery={searchQuery}
            sortBy={typedSortBy}
            sortOrder={typedSortOrder}
            isSelectable={true}
            selectedItems={bulkOperations.selectedItems}
            onToggleSelect={bulkOperations.toggleItem}
            onSelectAll={(items) => bulkOperations.selectAll(toBulkOperationItems(items))}
            onDeselectAll={bulkOperations.deselectAll}
          />
        </CardContent>
      </Card>
    </div>
  )
}

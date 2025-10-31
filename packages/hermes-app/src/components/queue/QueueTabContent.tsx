import { Card, CardContent } from '@/components/ui/card'
import { QueueList } from './QueueList'
import { QueueStats } from './QueueStats'
import { BulkOperations } from './BulkOperations'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'
import { useBulkOperations } from '@/hooks/useBulkOperations'

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
  const { data: queueData } = useQuery({
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

  return (
    <div className="space-y-4">
      {showStats && <QueueStats />}

      {/* Bulk Operations Toolbar */}
      <BulkOperations
        selectedCount={bulkOperations.selectedCount}
        totalCount={queueData?.items?.length || 0}
        selectedItems={bulkOperations.getSelectedItems(
          queueData?.items?.map((item: components["schemas"]["DownloadStatus"]) => ({
            id: item.download_id,
            title: String(item.result?.title || item.download_id),
            filePath: item.current_filename || undefined,
            status: item.status
          })) || []
        )}
        onSelectAll={() => {
          if (queueData?.items) {
            bulkOperations.selectAll(queueData.items.map((item: components["schemas"]["DownloadStatus"]) => ({
              id: item.download_id,
              title: String(item.result?.title || item.download_id),
              filePath: item.current_filename || undefined,
              status: item.status
            })))
          }
        }}
        onDeselectAll={bulkOperations.deselectAll}
        onBulkDelete={() => bulkOperations.bulkDelete(
          queueData?.items?.map((item: components["schemas"]["DownloadStatus"]) => ({
            id: item.download_id,
            title: String(item.result?.title || item.download_id),
            filePath: item.current_filename || undefined,
            status: item.status
          })) || []
        )}
        onBulkCancel={() => {}} // TODO: Implement bulk cancel
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
            onSelectAll={(items) => bulkOperations.selectAll(
              items.map(item => ({
                id: item.download_id,
                title: String(item.result?.title || item.download_id),
                filePath: item.current_filename || undefined,
                status: item.status
              }))
            )}
            onDeselectAll={bulkOperations.deselectAll}
          />
        </CardContent>
      </Card>
    </div>
  )
}

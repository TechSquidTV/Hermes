import type { components } from '@/types/api.generated'

export type DownloadStatus = components["schemas"]["DownloadStatus"]
export type QueueViewMode = 'active' | 'history' | 'all'

const ACTIVE_STATUS_FILTERS = new Set(['downloading', 'queued', 'processing', 'failed'])

export interface BulkOperationItem {
  id: string
  title: string
  filePath?: string
  status: string
}

export function getQueueStatusFilter(
  viewMode: QueueViewMode,
  statusFilter: string
): string | undefined {
  if (viewMode === 'active') {
    return ACTIVE_STATUS_FILTERS.has(statusFilter) ? statusFilter : undefined
  }

  if (viewMode === 'history') {
    return 'completed'
  }

  return undefined
}

export function getQueueDisplayStatusFilter(
  viewMode: QueueViewMode,
  statusFilter: string
): string {
  if (viewMode === 'active') {
    return ACTIVE_STATUS_FILTERS.has(statusFilter) ? statusFilter : 'all'
  }

  if (viewMode === 'history') {
    return statusFilter === 'completed' ? 'completed' : 'all'
  }

  return statusFilter
}

export function getVisibleQueueItems(
  items: DownloadStatus[],
  viewMode: QueueViewMode
): DownloadStatus[] {
  if (viewMode === 'active') {
    return items.filter(
      (item) =>
        item.status !== 'completed' ||
        (item.status === 'completed' && !(item.result as { completed_at?: string })?.completed_at)
    )
  }

  if (viewMode === 'history') {
    return items.filter((item) => item.status === 'completed')
  }

  return items
}

export function toBulkOperationItem(item: DownloadStatus): BulkOperationItem {
  return {
    id: item.downloadId,
    title: String(item.result?.title || item.downloadId),
    filePath: item.currentFilename || undefined,
    status: item.status,
  }
}

export function toBulkOperationItems(
  items: DownloadStatus[] | null | undefined
): BulkOperationItem[] {
  return items?.map(toBulkOperationItem) || []
}

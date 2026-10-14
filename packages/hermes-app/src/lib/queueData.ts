import type { components } from '@/types/api.generated'

export type DownloadStatus = components['schemas']['DownloadStatus']
export type QueueViewMode = 'active' | 'history' | 'all'
const ACTIVE_STATUS_FILTERS = new Set(['pending', 'downloading', 'processing', 'failed', 'cancelled'])
export interface BulkOperationItem { id: string; title: string; filePath?: string; status: string }

export function isActiveDownloadStatus(status: string | undefined): boolean {
  return status === 'pending' || status === 'downloading' || status === 'processing'
}

export function getQueueStatusFilter(viewMode: QueueViewMode, statusFilter: string): string | undefined {
  const display = getQueueDisplayStatusFilter(viewMode, statusFilter)
  return display === 'all' ? undefined : display
}

export function getQueueDisplayStatusFilter(viewMode: QueueViewMode, statusFilter: string): string {
  if (viewMode === 'active') return ACTIVE_STATUS_FILTERS.has(statusFilter) ? statusFilter : 'all'
  if (viewMode === 'history') return 'completed'
  return statusFilter
}

export function getVisibleQueueItems(items: DownloadStatus[], viewMode: QueueViewMode): DownloadStatus[] {
  if (viewMode === 'active') return items.filter(item => item.status !== 'completed')
  if (viewMode === 'history') return items.filter(item => item.status === 'completed')
  return items
}

export function toBulkOperationItem(item: DownloadStatus): BulkOperationItem {
  return { id: item.downloadId, title: item.result?.title || item.downloadId, filePath: item.currentFilename || undefined, status: item.status }
}
export function toBulkOperationItems(items: DownloadStatus[] | null | undefined): BulkOperationItem[] {
  return items?.map(toBulkOperationItem) ?? []
}

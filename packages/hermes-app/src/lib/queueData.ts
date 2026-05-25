import type { components } from '@/types/api.generated'

export type DownloadStatus = components["schemas"]["DownloadStatus"]
export type QueueViewMode = 'active' | 'history' | 'all'

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
    return statusFilter === 'all' ? undefined : statusFilter
  }

  if (viewMode === 'history') {
    return 'completed'
  }

  return undefined
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

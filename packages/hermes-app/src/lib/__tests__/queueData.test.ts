import { describe, expect, it } from 'vitest'
import {
  getQueueStatusFilter,
  toBulkOperationItem,
  toBulkOperationItems,
  type DownloadStatus,
} from '../queueData'

describe('queueData helpers', () => {
  it('resolves queue status filters from view state', () => {
    expect(getQueueStatusFilter('active', 'all')).toBeUndefined()
    expect(getQueueStatusFilter('active', 'downloading')).toBe('downloading')
    expect(getQueueStatusFilter('history', 'failed')).toBe('completed')
    expect(getQueueStatusFilter('all', 'failed')).toBeUndefined()
  })

  it('maps download status records into bulk operation items', () => {
    const item = {
      downloadId: 'download-123',
      status: 'completed',
      currentFilename: '/downloads/video.mp4',
      result: {
        title: 'Video title',
      },
      message: 'Download completed',
      createdAt: '2026-01-01T00:00:00Z',
    } as DownloadStatus

    expect(toBulkOperationItem(item)).toEqual({
      id: 'download-123',
      title: 'Video title',
      filePath: '/downloads/video.mp4',
      status: 'completed',
    })
  })

  it('falls back to download id and handles empty lists', () => {
    const item = {
      downloadId: 'download-123',
      status: 'queued',
      message: 'Queued',
      createdAt: '2026-01-01T00:00:00Z',
    } as DownloadStatus

    expect(toBulkOperationItems([item])).toEqual([
      {
        id: 'download-123',
        title: 'download-123',
        filePath: undefined,
        status: 'queued',
      },
    ])
    expect(toBulkOperationItems(undefined)).toEqual([])
  })
})

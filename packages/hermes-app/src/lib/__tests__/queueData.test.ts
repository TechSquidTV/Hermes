import { describe, expect, it } from 'vitest'
import {
  getQueueDisplayStatusFilter,
  getQueueStatusFilter,
  getVisibleQueueItems,
  toBulkOperationItem,
  toBulkOperationItems,
  type DownloadStatus,
} from '../queueData'

describe('queueData helpers', () => {
  it('resolves queue status filters from view state', () => {
    expect(getQueueStatusFilter('active', 'all')).toBeUndefined()
    expect(getQueueStatusFilter('active', 'downloading')).toBe('downloading')
    expect(getQueueStatusFilter('active', 'completed')).toBeUndefined()
    expect(getQueueStatusFilter('history', 'failed')).toBe('completed')
    expect(getQueueStatusFilter('all', 'failed')).toBeUndefined()
  })

  it('normalizes stale status filters for visible queue data', () => {
    expect(getQueueDisplayStatusFilter('active', 'completed')).toBe('all')
    expect(getQueueDisplayStatusFilter('active', 'failed')).toBe('failed')
    expect(getQueueDisplayStatusFilter('history', 'failed')).toBe('all')
    expect(getQueueDisplayStatusFilter('history', 'completed')).toBe('completed')
    expect(getQueueDisplayStatusFilter('all', 'failed')).toBe('failed')
  })

  it('filters queue items by visible view mode', () => {
    const items = [
      { downloadId: 'queued', status: 'queued' },
      { downloadId: 'completed', status: 'completed' },
      {
        downloadId: 'active-completed',
        status: 'completed',
        result: {},
      },
      {
        downloadId: 'history-completed',
        status: 'completed',
        result: { completed_at: '2026-01-01T00:00:00Z' },
      },
    ] as DownloadStatus[]

    expect(getVisibleQueueItems(items, 'active').map((item) => item.downloadId)).toEqual([
      'queued',
      'completed',
      'active-completed',
    ])
    expect(getVisibleQueueItems(items, 'history').map((item) => item.downloadId)).toEqual([
      'completed',
      'active-completed',
      'history-completed',
    ])
    expect(getVisibleQueueItems(items, 'all')).toEqual(items)
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

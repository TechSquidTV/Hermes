/**
 * Tests for useBulkOperations hook.
 *
 * The API client and delete mutation are mocked so these tests cover the hook's
 * selection, filtering, cleanup, and error-handling logic.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import { useBulkOperations } from '../useBulkOperations'
import { useDeleteFiles } from '../useDownloadActions'

vi.mock('../useDownloadActions', () => ({
  useDeleteFiles: vi.fn(),
}))

vi.mock('@/services/api/client', () => ({
  apiClient: {
    cancelDownload: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}))

const mutateAsync = vi.fn()
const mockUseDeleteFiles = vi.mocked(useDeleteFiles)
const mockCancelDownload = vi.mocked(apiClient.cancelDownload)
const mockToast = vi.mocked(toast)

type BulkItem = Parameters<
  ReturnType<typeof useBulkOperations>['bulkDelete']
>[0][number]

function renderBulkOperations(options?: Parameters<typeof useBulkOperations>[0]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )

  return {
    ...renderHook(() => useBulkOperations(options), { wrapper }),
    invalidateQueries,
  }
}

describe('useBulkOperations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseDeleteFiles.mockReturnValue(
      { mutateAsync } as unknown as ReturnType<typeof useDeleteFiles>
    )
    mutateAsync.mockResolvedValue({
      deletedFiles: 1,
      failedDeletions: [],
      totalFreedSpace: 1024,
    })
    mockCancelDownload.mockResolvedValue({
      downloadId: 'download-1',
      cancelled: true,
      message: 'Cancelled',
    })
  })

  it('rejects bulk delete when nothing is selected', async () => {
    const { result } = renderBulkOperations()

    await act(async () => {
      await result.current.bulkDelete([])
    })

    expect(mockToast.error).toHaveBeenCalledWith('No items selected')
    expect(mutateAsync).not.toHaveBeenCalled()
    expect(result.current.isProcessing).toBe(false)
  })

  it('rejects bulk delete when selected items have no file paths', async () => {
    const items: BulkItem[] = [
      { id: 'download-1', title: 'No file yet', status: 'completed' },
    ]
    const { result } = renderBulkOperations()

    act(() => {
      result.current.selectItem('download-1')
    })
    await act(async () => {
      await result.current.bulkDelete(items)
    })

    expect(mockToast.error).toHaveBeenCalledWith(
      'No downloadable files found in selection'
    )
    expect(mutateAsync).not.toHaveBeenCalled()
    expect(result.current.selectedCount).toBe(1)
  })

  it('deletes only selected files with paths and clears selection on success', async () => {
    const onSuccess = vi.fn()
    const items: BulkItem[] = [
      {
        id: 'download-1',
        title: 'Selected with file',
        filePath: '/downloads/one.mp4',
        status: 'completed',
      },
      {
        id: 'download-2',
        title: 'Selected without file',
        status: 'completed',
      },
      {
        id: 'download-3',
        title: 'Unselected with file',
        filePath: '/downloads/three.mp4',
        status: 'completed',
      },
    ]
    const { result } = renderBulkOperations({ onSuccess })

    act(() => {
      result.current.selectItem('download-1')
      result.current.selectItem('download-2')
    })
    await act(async () => {
      await result.current.bulkDelete(items)
    })

    expect(mutateAsync).toHaveBeenCalledWith(['/downloads/one.mp4'])
    expect(onSuccess).toHaveBeenCalledTimes(1)
    expect(result.current.selectedCount).toBe(0)
    expect(result.current.isProcessing).toBe(false)
  })

  it('cancels only selected queued, downloading, or processing items', async () => {
    const onSuccess = vi.fn()
    const items: BulkItem[] = [
      { id: 'queued', title: 'Queued', status: 'queued' },
      { id: 'downloading', title: 'Downloading', status: 'downloading' },
      { id: 'processing', title: 'Processing', status: 'processing' },
      { id: 'completed', title: 'Completed', status: 'completed' },
      { id: 'unselected', title: 'Unselected', status: 'queued' },
    ]
    const { result, invalidateQueries } = renderBulkOperations({ onSuccess })

    act(() => {
      result.current.selectItem('queued')
      result.current.selectItem('downloading')
      result.current.selectItem('processing')
      result.current.selectItem('completed')
    })
    await act(async () => {
      await result.current.bulkCancel(items)
    })

    expect(mockCancelDownload).toHaveBeenCalledTimes(3)
    expect(mockCancelDownload).toHaveBeenCalledWith('queued')
    expect(mockCancelDownload).toHaveBeenCalledWith('downloading')
    expect(mockCancelDownload).toHaveBeenCalledWith('processing')
    expect(mockCancelDownload).not.toHaveBeenCalledWith('completed')
    expect(mockCancelDownload).not.toHaveBeenCalledWith('unselected')
    expect(mockToast.success).toHaveBeenCalledWith('Cancelled 3 downloads')
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['queue'],
      exact: false,
    })
    expect(invalidateQueries).toHaveBeenCalledTimes(1)
    expect(onSuccess).toHaveBeenCalledTimes(1)
    expect(result.current.selectedCount).toBe(0)
  })

  it('reports bulk cancel failures and preserves the selection', async () => {
    const onError = vi.fn()
    const items: BulkItem[] = [
      { id: 'queued', title: 'Queued', status: 'queued' },
    ]
    mockCancelDownload.mockRejectedValueOnce(new Error('Network failed'))
    const { result } = renderBulkOperations({ onError })

    act(() => {
      result.current.selectItem('queued')
    })
    await act(async () => {
      await result.current.bulkCancel(items)
    })

    expect(mockToast.error).toHaveBeenCalledWith(
      'Failed to cancel downloads: Network failed'
    )
    expect(onError).toHaveBeenCalledWith(expect.any(Error))
    expect(result.current.selectedCount).toBe(1)
    expect(result.current.isProcessing).toBe(false)
  })
})

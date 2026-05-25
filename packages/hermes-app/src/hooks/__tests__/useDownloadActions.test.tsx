import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'sonner'
import { apiClient } from '@/services/api/client'
import {
  useCancelDownload,
  useDeleteFiles,
  useStartDownload,
} from '../useDownloadActions'

vi.mock('@/services/api/client', () => ({
  apiClient: {
    startDownload: vi.fn(),
    deleteFiles: vi.fn(),
    cancelDownload: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}))

const mockStartDownload = vi.mocked(apiClient.startDownload)
const mockDeleteFiles = vi.mocked(apiClient.deleteFiles)
const mockCancelDownload = vi.mocked(apiClient.cancelDownload)
const mockToast = vi.mocked(toast)

function renderWithQueryClient<T>(hook: () => T) {
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
    ...renderHook(hook, { wrapper }),
    invalidateQueries,
  }
}

describe('useDownloadActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStartDownload.mockResolvedValue({
      downloadId: 'download-1',
      status: 'pending',
      message: 'Queued',
    })
    mockDeleteFiles.mockResolvedValue({
      deletedFiles: 1,
      failedDeletions: [],
      totalFreedSpace: 1024 * 1024,
    })
    mockCancelDownload.mockResolvedValue({
      downloadId: 'download-1',
      cancelled: true,
      message: 'Cancelled',
    })
  })

  it('invalidates queue data after starting a download', async () => {
    const { result, invalidateQueries } = renderWithQueryClient(useStartDownload)

    await act(async () => {
      await result.current.mutateAsync({
        url: 'https://example.test/watch',
        format: 'best',
        downloadSubtitles: false,
        downloadThumbnail: false,
      })
    })

    expect(mockStartDownload).toHaveBeenCalledWith({
      url: 'https://example.test/watch',
      format: 'best',
      downloadSubtitles: false,
      downloadThumbnail: false,
    })
    expect(mockToast.success).toHaveBeenCalledWith(
      'Download started successfully!'
    )
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['queue'],
      exact: false,
    })
    expect(invalidateQueries).toHaveBeenCalledTimes(1)
  })

  it('invalidates queue and files data after deleting files', async () => {
    const { result, invalidateQueries } = renderWithQueryClient(useDeleteFiles)

    await act(async () => {
      await result.current.mutateAsync(['/downloads/video.mp4'])
    })

    expect(mockDeleteFiles).toHaveBeenCalledWith(['/downloads/video.mp4'])
    expect(mockToast.success).toHaveBeenCalledWith('Files deleted! Freed 1.00 MB')
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['queue'],
      exact: false,
    })
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['files'],
      exact: false,
    })
    expect(invalidateQueries).toHaveBeenCalledTimes(2)
  })

  it('invalidates queue data after cancelling a download', async () => {
    const { result, invalidateQueries } = renderWithQueryClient(useCancelDownload)

    await act(async () => {
      await result.current.mutateAsync('download-1')
    })

    expect(mockCancelDownload).toHaveBeenCalledWith('download-1')
    expect(mockToast.success).toHaveBeenCalledWith('Download cancelled')
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['queue'],
      exact: false,
    })
    expect(invalidateQueries).toHaveBeenCalledTimes(1)
  })
})

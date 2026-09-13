import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'sonner'
import { apiClient } from '@/services/api/client'
import { TokenStorage } from '@/utils/tokenStorage'
import {
  useCancelDownload,
  useDeleteFiles,
  useDownloadFile,
  useStartDownload,
} from '../useDownloadActions'

vi.mock('@/services/api/client', () => ({
  apiClient: {
    startDownload: vi.fn(),
    deleteFiles: vi.fn(),
    cancelDownload: vi.fn(),
    getDownloadFileUrl: vi.fn(() => '/api/v1/files/download?path=video.mp4'),
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
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

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

  it.each([
    {
      status: 404,
      body: '{"detail":"File not found"}',
      statusText: '',
      message: 'Download failed: HTTP 404: {"detail":"File not found"}',
    },
    {
      status: 500,
      body: '{"error":{"message":"Storage unavailable"}}',
      statusText: '',
      message: 'Download failed: HTTP 500: {"error":{"message":"Storage unavailable"}}',
    },
    {
      status: 502,
      body: 'Bad gateway from storage',
      statusText: '',
      message: 'Download failed: HTTP 502: Bad gateway from storage',
    },
    {
      status: 403,
      body: '',
      statusText: 'Forbidden',
      message: 'Download failed: HTTP 403: Forbidden',
    },
    {
      status: 503,
      body: '',
      statusText: '',
      message: 'Download failed: HTTP 503',
    },
  ])(
    'shows HTTP $status and the API error body when file retrieval fails',
    async ({ status, body, statusText, message }) => {
      vi.spyOn(TokenStorage, 'getAccessToken').mockReturnValue('access-token')
      const fetchMock = vi.fn<typeof fetch>()
        .mockResolvedValue(new Response(body, { status, statusText }))
      vi.stubGlobal('fetch', fetchMock)
      const { result } = renderWithQueryClient(useDownloadFile)

      await act(async () => {
        await expect(result.current.mutateAsync({
          filePath: '/downloads/video.mp4',
          title: 'Video',
        })).rejects.toThrow(message)
      })

      expect(mockToast.error).toHaveBeenCalledWith(`Failed to download file: ${message}`)
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/files/download?path=video.mp4', {
        headers: { Authorization: 'Bearer access-token' },
      })
    }
  )

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

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DownloadEventsProvider } from '@/contexts/DownloadEventsContext'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'
import { useDownloadProgressSSE } from './useDownloadProgressSSE'

vi.mock('@/services/api/client', () => ({
  apiClient: { createSSEToken: vi.fn(), getDownloadStatus: vi.fn() },
}))
class Source extends EventTarget {
  static CLOSED = 2
  static instances: Source[] = []
  readyState = 0
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  close = vi.fn(() => {
    this.readyState = Source.CLOSED
  })
  constructor(public url: string) {
    super()
    Source.instances.push(this)
  }
  emit(data: object) {
    this.dispatchEvent(new MessageEvent('download_progress', { data: JSON.stringify(data) }))
  }
}
const snapshot = (id: string): components['schemas']['DownloadStatus'] => ({
  downloadId: id,
  status: 'downloading',
  message: 'Downloading',
  createdAt: '2026-10-13T12:00:00Z',
  progress: { percentage: 10 },
  result: { title: `Video ${id}` },
})
function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <DownloadEventsProvider enabled>{children}</DownloadEventsProvider>
    </QueryClientProvider>
  )
  return { client, wrapper }
}
beforeEach(() => {
  vi.resetAllMocks()
  Source.instances = []
  vi.stubGlobal('EventSource', Source)
  vi.mocked(apiClient.createSSEToken).mockResolvedValue({
    token: 'ephemeral',
    expiresAt: new Date(Date.now() + 600_000).toISOString(),
    scope: 'downloads',
    permissions: ['read'],
    ttl: 600,
  })
  vi.mocked(apiClient.getDownloadStatus).mockImplementation(async (id) => snapshot(id))
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('shared download progress', () => {
  it('opens one scoped connection for many cards and deduplicates HTTP observers', async () => {
    const { wrapper } = setup()
    const { result, unmount } = renderHook(
      () =>
        [
          useDownloadProgressSSE('a'),
          useDownloadProgressSSE('b'),
          useDownloadProgressSSE('a'),
        ] as const,
      { wrapper }
    )
    await waitFor(() => expect(result.current[0].data?.status).toBe('downloading'))
    expect(Source.instances).toHaveLength(1)
    expect(apiClient.createSSEToken).toHaveBeenCalledWith(
      { scope: 'downloads', ttl: 600 },
      expect.any(AbortSignal)
    )
    expect(apiClient.getDownloadStatus).toHaveBeenCalledTimes(2)
    const source = Source.instances[0]!
    act(() => source.onopen?.())
    expect(result.current[0].isConnected).toBe(true)
    unmount()
    expect(source.close).toHaveBeenCalled()
  })

  it('normalizes worker fields and updates only the matching cache entry', async () => {
    const { wrapper } = setup()
    const { result } = renderHook(
      () => [useDownloadProgressSSE('a'), useDownloadProgressSSE('b')] as const,
      { wrapper }
    )
    await waitFor(() => expect(result.current[1].data).not.toBeNull())
    act(() =>
      Source.instances[0]!.emit({
        download_id: 'a',
        status: 'downloading',
        progress: { percentage: 45, downloaded_bytes: 512, total_bytes: 1024, speed: 50, eta: 10 },
      })
    )
    await waitFor(() => expect(result.current[0].data?.progress?.downloadedBytes).toBe(512))
    expect(result.current[0].data?.result?.title).toBe('Video a')
    expect(result.current[1].data?.progress?.percentage).toBe(10)
    act(() =>
      Source.instances[0]!.emit({
        download_id: 'a',
        status: 'completed',
        output_path: 'nested/a.mp4',
        result: { file_size: 1024 },
      })
    )
    await waitFor(() => expect(result.current[0].data?.currentFilename).toBe('nested/a.mp4'))
    expect(result.current[0].data?.result?.fileSize).toBe(1024)
  })

  it('does not let an older HTTP snapshot overwrite a newer live event', async () => {
    let finish!: (value: components['schemas']['DownloadStatus']) => void
    vi.mocked(apiClient.getDownloadStatus).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        })
    )
    const { wrapper } = setup()
    const { result } = renderHook(() => useDownloadProgressSSE('a'), { wrapper })
    await waitFor(() => expect(Source.instances).toHaveLength(1))
    act(() =>
      Source.instances[0]!.emit({ download_id: 'a', status: 'completed', output_path: 'a.mp4' })
    )
    await waitFor(() => expect(result.current.data?.status).toBe('completed'))
    await act(async () => finish(snapshot('a')))
    expect(result.current.data?.status).toBe('completed')
  })

  it('polls while disconnected and stops polling after connecting', async () => {
    vi.useFakeTimers()
    const { wrapper } = setup()
    const { result } = renderHook(() => useDownloadProgressSSE('a'), { wrapper })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(apiClient.getDownloadStatus).toHaveBeenCalledTimes(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(apiClient.getDownloadStatus).toHaveBeenCalledTimes(2)
    act(() => Source.instances[0]!.onopen?.())
    expect(result.current.isConnected).toBe(true)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(apiClient.getDownloadStatus).toHaveBeenCalledTimes(2)
  })

  it('keeps completed downloads from polling after a disconnected snapshot', async () => {
    vi.useFakeTimers()
    vi.mocked(apiClient.getDownloadStatus).mockResolvedValue({
      ...snapshot('a'),
      status: 'completed',
    })
    const { wrapper } = setup()
    renderHook(() => useDownloadProgressSSE('a'), { wrapper })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(apiClient.getDownloadStatus).toHaveBeenCalledOnce()
  })
})

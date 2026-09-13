import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/services/api/client'
import { taskTracker } from '@/lib/taskTracking'
import { VideoPreview } from '../VideoPreview'

describe('VideoPreview download format', () => {
  afterEach(() => vi.restoreAllMocks())

  it('requests adaptive streams for Best Quality', async () => {
    const user = userEvent.setup()
    const onDownload = vi.fn()
    render(
      <QueryClientProvider client={new QueryClient()}>
        <VideoPreview
          info={{ id: 'video', title: 'Video', webpageUrl: 'https://example.test/video', extractor: 'test' }}
          onDownload={onDownload}
        />
      </QueryClientProvider>,
    )

    expect(screen.getByText('Best Quality')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Download Video' }))
    expect(onDownload).toHaveBeenCalledWith('bestvideo*+bestaudio/best')
  })

  it('uses the same default for playlist batches', async () => {
    const user = userEvent.setup()
    const startBatch = vi.spyOn(apiClient, 'startBatchDownload').mockResolvedValue({
      batchId: 'batch', totalDownloads: 1, status: 'pending', downloads: ['download'],
    })
    vi.spyOn(taskTracker, 'addTask').mockImplementation(() => {})
    render(
      <QueryClientProvider client={new QueryClient()}>
        <VideoPreview
          info={{
            id: 'playlist', title: 'Playlist', webpageUrl: 'https://example.test/playlist',
            extractor: 'test', playlistCount: 1,
            entries: [{ id: 'video', title: 'Video', url: 'https://example.test/video' }],
          }}
        />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Download 1 Video' }))
    await waitFor(() => expect(startBatch).toHaveBeenCalledWith(expect.objectContaining({
      urls: ['https://example.test/video'], format: 'bestvideo*+bestaudio/best',
    })))
  })
})

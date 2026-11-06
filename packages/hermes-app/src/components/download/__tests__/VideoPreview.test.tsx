import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/services/api/client'
import { taskTracker } from '@/lib/taskTracking'
import { toast } from 'sonner'
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
      batchId: 'batch', totalDownloads: 1, status: 'queued', downloads: ['download'], failedDownloads: [],
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

  it.each([['partial', ['two']], ['failed', ['one', 'two']]] as const)(
    'reports %s publication without counting failed videos as queued', async (status, failedDownloads) => {
      const user = userEvent.setup()
      const success = vi.spyOn(toast, 'success')
      const error = vi.spyOn(toast, 'error')
      vi.spyOn(apiClient, 'startBatchDownload').mockResolvedValue({
        batchId: 'batch', totalDownloads: 2, status, downloads: ['one', 'two'], failedDownloads: [...failedDownloads],
      })
      const track = vi.spyOn(taskTracker, 'addTask').mockImplementation(() => {})
      const client = new QueryClient()
      const invalidate = vi.spyOn(client, 'invalidateQueries')
      render(
        <QueryClientProvider client={client}>
          <VideoPreview info={{
            id: 'playlist', title: 'Playlist', webpageUrl: 'https://example.test/playlist', extractor: 'test', playlistCount: 2,
            entries: ['one', 'two'].map(id => ({ id, title: id, url: `https://example.test/${id}` })),
          }} />
        </QueryClientProvider>,
      )

      await user.click(screen.getByRole('button', { name: 'Download 2 Videos' }))
      await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['queue'], exact: false }))
      expect(error).toHaveBeenCalledWith(`${failedDownloads.length} downloads could not be queued. Retry the failed items shown in the queue.`)
      expect(track).toHaveBeenCalledWith('one')
      expect(track).toHaveBeenCalledWith('two')
      if (status === 'partial') expect(success).toHaveBeenCalledWith('Successfully queued 1 video in 1 batch')
      else expect(success).not.toHaveBeenCalled()
    },
  )
})

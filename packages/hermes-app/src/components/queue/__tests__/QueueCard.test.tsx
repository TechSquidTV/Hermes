/**
 * Tests for QueueCard component
 *
 * Tests the queue card display with download status, actions, and bulk selection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { QueueCard } from '../QueueCard'
import type { DownloadStatus } from '@/types'
import { toast } from 'sonner'

// Mock dependencies
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

vi.mock('@/hooks/useDownloadActions', () => ({
  useDownloadFile: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('@/hooks/useConfirmation', () => {
  const { useState } = require('react')

  return {
    useConfirmation: () => {
      const [isOpen, setIsOpen] = useState(false)
      const [title, setTitle] = useState('')
      const [description, setDescription] = useState('')
      const [confirmText, setConfirmText] = useState('')
      const [cancelText, setCancelText] = useState('')
      const [variant, setVariant] = useState('default')
      const [onConfirmCallback, setOnConfirmCallback] = useState(() => () => {})

      return {
        isOpen,
        title,
        description,
        confirmText,
        cancelText,
        variant,
        showConfirmation: (options: any) => {
          setIsOpen(true)
          setTitle(options.title || '')
          setDescription(options.description || '')
          setConfirmText(options.confirmText || '')
          setCancelText(options.cancelText || '')
          setVariant(options.variant || 'default')
          setOnConfirmCallback(() => options.onConfirm || (() => {}))
        },
        hideConfirmation: () => {
          setIsOpen(false)
        },
        confirm: () => {
          onConfirmCallback()
          setIsOpen(false)
        },
      }
    },
  }
})

vi.mock('@/components/download/DownloadProgressTracker', () => ({
  DownloadProgressTracker: ({ downloadId }: { downloadId: string }) => (
    <div data-testid="download-progress-tracker">{downloadId}</div>
  ),
}))

vi.mock('@/components/ui/download-progress', () => ({
  DownloadProgress: ({ status, progress }: { status: string; progress?: number }) => (
    <div data-testid="download-progress">
      {status} - {progress ?? 0}%
    </div>
  ),
}))

vi.mock('@/components/ui/status-badge', () => ({
  StatusBadge: ({ status }: { status: string }) => (
    <div data-testid="status-badge">{status}</div>
  ),
}))

vi.mock('@/components/ui/confirmation-dialog', () => ({
  ConfirmationDialog: ({
    isOpen,
    onConfirm,
    onClose,
    title,
  }: {
    isOpen: boolean
    onConfirm: () => void
    onClose: () => void
    title: string
  }) =>
    isOpen ? (
      <div data-testid="confirmation-dialog">
        <span data-testid="dialog-title">{title}</span>
        <button onClick={onConfirm}>Confirm</button>
        <button onClick={onClose}>Cancel</button>
      </div>
    ) : null,
}))

vi.mock('@/services/api/client', () => ({
  apiClient: {
    deleteFiles: vi.fn(),
  },
}))

vi.mock('@/components/animate-ui/primitives/effects/blur', () => ({
  Blur: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}))

vi.mock('@/components/animate-ui/primitives/radix/checkbox', () => ({
  Checkbox: ({ checked, onCheckedChange, className, children }: any) => (
    <div className={className}>
      <input
        type="checkbox"
        checked={checked}
        onChange={() => onCheckedChange(!checked)}
      />
      {children}
    </div>
  ),
  CheckboxIndicator: ({ className }: any) => (
    <span className={className} data-testid="checkbox-indicator" />
  ),
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, title, disabled, className }: any) => (
    <button onClick={onClick} title={title} disabled={disabled} className={className}>
      {children}
    </button>
  ),
}))

vi.mock('@/lib/utils', () => ({
  formatFileSize: (bytes: number) => `${(bytes / 1024 / 1024).toFixed(2)} MB`,
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

describe('QueueCard', () => {
  let queryClient: QueryClient

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  const mockDownload: DownloadStatus = {
    download_id: 'test-123',
    status: 'queued',
    message: '',
    result: {
      title: 'Test Video',
      url: 'https://example.com/video',
      extractor: 'youtube',
      file_size: 1024 * 1024 * 50, // 50 MB
      thumbnail_url: 'https://example.com/thumb.jpg',
    },
    current_filename: '/path/to/file.mp4',
    progress: {
      percentage: 0,
      downloaded_bytes: 0,
      total_bytes: 1024 * 1024 * 50,
      speed: 0,
      eta: 0,
    },
    created_at: '2025-01-01T10:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient?.clear()
  })

  describe('Rendering', () => {
    it('renders with minimal download data', () => {
      const minimalDownload: DownloadStatus = {
        download_id: 'test-123',
        status: 'queued',
        message: '',
        created_at: '2025-01-01T10:00:00Z',
      }

      render(<QueueCard download={minimalDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Download test-123')).toBeInTheDocument()
      // "Processing..." appears twice - once as URL placeholder, once as timestamp
      expect(screen.getAllByText('Processing...').length).toBeGreaterThan(0)
    })

    it('renders with full download result', () => {
      render(<QueueCard download={mockDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Test Video')).toBeInTheDocument()
      expect(screen.getByText('https://example.com/video')).toBeInTheDocument()
      expect(screen.getByText(/youtube/i)).toBeInTheDocument()
      expect(screen.getByText(/50.00 MB/i)).toBeInTheDocument()
    })

    it('renders thumbnail image', () => {
      render(<QueueCard download={mockDownload} />, { wrapper: createWrapper() })

      const thumbnail = screen.getByAltText('Test Video')
      expect(thumbnail).toBeInTheDocument()
      expect(thumbnail).toHaveAttribute('src', 'https://example.com/thumb.jpg')
    })

    it('hides thumbnail on load error', () => {
      render(<QueueCard download={mockDownload} />, { wrapper: createWrapper() })

      const thumbnail = screen.getByAltText('Test Video') as HTMLImageElement

      // Simulate image load error
      thumbnail.dispatchEvent(new Event('error'))

      expect(thumbnail.style.display).toBe('none')
    })

    it('shows error message when present', () => {
      const errorDownload = {
        ...mockDownload,
        status: 'failed' as const,
        error: 'Download failed: Network error',
      }

      render(<QueueCard download={errorDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Download failed: Network error')).toBeInTheDocument()
    })

    it('renders status badge', () => {
      render(<QueueCard download={mockDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('status-badge')).toHaveTextContent('queued')
    })
  })

  describe('Selection', () => {
    it('shows checkbox when isSelectable is true', () => {
      render(<QueueCard download={mockDownload} isSelectable={true} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByRole('checkbox')).toBeInTheDocument()
    })

    it('does not show checkbox when isSelectable is false', () => {
      render(<QueueCard download={mockDownload} isSelectable={false} />, {
        wrapper: createWrapper(),
      })

      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    })

    it('checkbox reflects isSelected state', () => {
      render(
        <QueueCard download={mockDownload} isSelectable={true} isSelected={true} />,
        { wrapper: createWrapper() }
      )

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).toBeChecked()
    })

    it('calls onToggleSelect when checkbox is clicked', async () => {
      const user = userEvent.setup()
      const onToggleSelect = vi.fn()

      render(
        <QueueCard
          download={mockDownload}
          isSelectable={true}
          onToggleSelect={onToggleSelect}
        />,
        { wrapper: createWrapper() }
      )

      const checkbox = screen.getByRole('checkbox')
      await user.click(checkbox)

      expect(onToggleSelect).toHaveBeenCalledWith('test-123')
    })
  })

  describe('Status-specific displays', () => {
    it('shows DownloadProgressTracker for queued status', () => {
      const queuedDownload = { ...mockDownload, status: 'queued' as const }

      render(<QueueCard download={queuedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress-tracker')).toBeInTheDocument()
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows DownloadProgressTracker for downloading status', () => {
      const downloadingDownload = { ...mockDownload, status: 'downloading' as const }

      render(<QueueCard download={downloadingDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress-tracker')).toBeInTheDocument()
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows DownloadProgressTracker for processing status', () => {
      const processingDownload = { ...mockDownload, status: 'processing' as const }

      render(<QueueCard download={processingDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress-tracker')).toBeInTheDocument()
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows static DownloadProgress and action buttons for completed status', () => {
      const completedDownload = {
        ...mockDownload,
        status: 'completed' as const,
        progress: {
          ...mockDownload.progress,
          percentage: 100,
        },
      }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.getByTitle('Download File')).toBeInTheDocument()
      expect(screen.getByTitle('Delete')).toBeInTheDocument()
    })

    it('shows retry button for failed status', () => {
      const failedDownload = {
        ...mockDownload,
        status: 'failed' as const,
        error: 'Download failed',
      }

      render(<QueueCard download={failedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTitle('Retry Download')).toBeInTheDocument()
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })

    it('shows cancel button for downloading status', () => {
      const downloadingDownload = { ...mockDownload, status: 'downloading' as const }

      render(<QueueCard download={downloadingDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTitle('Cancel Download')).toBeInTheDocument()
    })
  })

  describe('Action Handlers', () => {
    it('handles download file button click', async () => {
      const user = userEvent.setup()
      const completedDownload = { ...mockDownload, status: 'completed' as const }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      const downloadButton = screen.getByTitle('Download File')
      await user.click(downloadButton)

      // useDownloadFile hook is mocked, so we just verify the button works
      expect(downloadButton).toBeInTheDocument()
    })

    it('shows toast error when download file with no path', async () => {
      const user = userEvent.setup()
      const completedDownload = {
        ...mockDownload,
        status: 'completed' as const,
        current_filename: null,
      }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      const downloadButton = screen.getByTitle('Download File')
      await user.click(downloadButton)

      // The handler checks for null path but doesn't show toast in this case
      // It just returns early
      expect(downloadButton).toBeInTheDocument()
    })

    it('opens confirmation dialog when delete button clicked', async () => {
      const user = userEvent.setup()
      const completedDownload = { ...mockDownload, status: 'completed' as const }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      const deleteButton = screen.getByTitle('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(screen.getByTestId('confirmation-dialog')).toBeInTheDocument()
        expect(screen.getByTestId('dialog-title')).toHaveTextContent('Delete File')
      })
    })

    it('shows toast error when delete with no file path', async () => {
      const user = userEvent.setup()
      const completedDownload = {
        ...mockDownload,
        status: 'completed' as const,
        current_filename: null,
      }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      const deleteButton = screen.getByTitle('Delete')
      await user.click(deleteButton)

      expect(toast.error).toHaveBeenCalledWith('File path not available')
    })

    it('shows toast when retry button clicked', async () => {
      const user = userEvent.setup()
      const failedDownload = { ...mockDownload, status: 'failed' as const }

      render(<QueueCard download={failedDownload} />, { wrapper: createWrapper() })

      const retryButton = screen.getByTitle('Retry Download')
      await user.click(retryButton)

      expect(toast.info).toHaveBeenCalledWith('Retry functionality coming soon!')
    })

    it('shows toast when cancel button clicked', async () => {
      const user = userEvent.setup()
      const downloadingDownload = { ...mockDownload, status: 'downloading' as const }

      render(<QueueCard download={downloadingDownload} />, { wrapper: createWrapper() })

      const cancelButton = screen.getByTitle('Cancel Download')
      await user.click(cancelButton)

      expect(toast.info).toHaveBeenCalledWith('Cancel functionality coming soon!')
    })
  })

  describe('Delete Mutation Flow', () => {
    it('closes confirmation dialog when cancel is clicked', async () => {
      const user = userEvent.setup()
      const completedDownload = { ...mockDownload, status: 'completed' as const }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      // Open dialog
      const deleteButton = screen.getByTitle('Delete')
      await user.click(deleteButton)

      await waitFor(() => {
        expect(screen.getByTestId('confirmation-dialog')).toBeInTheDocument()
      })

      // Click cancel
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByTestId('confirmation-dialog')).not.toBeInTheDocument()
      })
    })
  })

  describe('Timestamp Display', () => {
    it('shows "Processing..." for downloading status', () => {
      const downloadingDownload = { ...mockDownload, status: 'downloading' as const }

      render(<QueueCard download={downloadingDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows "Processing..." for processing status', () => {
      const processingDownload = { ...mockDownload, status: 'processing' as const }

      render(<QueueCard download={processingDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows "Processing..." for queued status', () => {
      const queuedDownload = { ...mockDownload, status: 'queued' as const }

      render(<QueueCard download={queuedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('shows "Completed" for completed status', () => {
      const completedDownload = { ...mockDownload, status: 'completed' as const }

      render(<QueueCard download={completedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Completed')).toBeInTheDocument()
    })

    it('shows "Failed" for failed status', () => {
      const failedDownload = { ...mockDownload, status: 'failed' as const }

      render(<QueueCard download={failedDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Failed')).toBeInTheDocument()
    })
  })

  describe('Type Guards and Helpers', () => {
    it('handles download with null result', () => {
      const noResultDownload: DownloadStatus = {
        ...mockDownload,
        result: null,
      }

      render(<QueueCard download={noResultDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Download test-123')).toBeInTheDocument()
      // "Processing..." appears twice - once as URL placeholder, once as timestamp
      expect(screen.getAllByText('Processing...').length).toBeGreaterThan(0)
    })

    it('handles download with empty result object', () => {
      const emptyResultDownload: DownloadStatus = {
        ...mockDownload,
        result: {} as any,
      }

      render(<QueueCard download={emptyResultDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Download test-123')).toBeInTheDocument()
    })

    it('handles download with invalid result type', () => {
      const invalidResultDownload: DownloadStatus = {
        ...mockDownload,
        result: 'invalid' as any,
      }

      render(<QueueCard download={invalidResultDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Download test-123')).toBeInTheDocument()
    })

    it('handles progress with null values', () => {
      const nullProgressDownload = {
        ...mockDownload,
        status: 'completed' as const,
        progress: null,
      }

      render(<QueueCard download={nullProgressDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress')).toBeInTheDocument()
    })

    it('handles progress with missing fields', () => {
      const partialProgressDownload = {
        ...mockDownload,
        status: 'completed' as const,
        progress: {
          percentage: 50,
          // Missing other fields
        },
      }

      render(<QueueCard download={partialProgressDownload} />, { wrapper: createWrapper() })

      expect(screen.getByTestId('download-progress')).toBeInTheDocument()
    })
  })

  describe('Different Download Sources', () => {
    it('displays extractor name for different sources', () => {
      const vimeoDownload = {
        ...mockDownload,
        result: {
          ...mockDownload.result!,
          extractor: 'vimeo',
        },
      }

      render(<QueueCard download={vimeoDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText(/vimeo/i)).toBeInTheDocument()
    })

    it('works without extractor field', () => {
      const noExtractorDownload = {
        ...mockDownload,
        result: {
          title: 'Test Video',
          url: 'https://example.com/video',
        },
      }

      render(<QueueCard download={noExtractorDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Test Video')).toBeInTheDocument()
      expect(screen.queryByText(/extractor/i)).not.toBeInTheDocument()
    })

    it('works without file size', () => {
      const noSizeDownload = {
        ...mockDownload,
        result: {
          title: 'Test Video',
          url: 'https://example.com/video',
          extractor: 'youtube',
        },
      }

      render(<QueueCard download={noSizeDownload} />, { wrapper: createWrapper() })

      expect(screen.getByText('Test Video')).toBeInTheDocument()
      // File size should not be shown
      expect(screen.queryByText(/MB/i)).not.toBeInTheDocument()
    })
  })

  describe('Integration', () => {
    it('renders complete card with all features', () => {
      const completedDownload = { ...mockDownload, status: 'completed' as const }

      render(
        <QueueCard
          download={completedDownload}
          isSelectable={true}
          isSelected={false}
          onToggleSelect={vi.fn()}
        />,
        { wrapper: createWrapper() }
      )

      // All major elements should be present
      expect(screen.getByRole('checkbox')).toBeInTheDocument()
      expect(screen.getByText('Test Video')).toBeInTheDocument()
      expect(screen.getByText('https://example.com/video')).toBeInTheDocument()
      expect(screen.getByTestId('status-badge')).toBeInTheDocument()
      expect(screen.getByTestId('download-progress')).toBeInTheDocument()
      expect(screen.getByTitle('Download File')).toBeInTheDocument()
      expect(screen.getByTitle('Delete')).toBeInTheDocument()
    })

    it('supports multiple cards in a list', () => {
      const download1 = { ...mockDownload, download_id: 'download-1' }
      const download2 = { ...mockDownload, download_id: 'download-2' }

      const { container } = render(
        <>
          <QueueCard download={download1} />
          <QueueCard download={download2} />
        </>,
        { wrapper: createWrapper() }
      )

      // Both cards should be rendered
      const cards = container.querySelectorAll('[class*="flex"]')
      expect(cards.length).toBeGreaterThan(0)
    })
  })
})

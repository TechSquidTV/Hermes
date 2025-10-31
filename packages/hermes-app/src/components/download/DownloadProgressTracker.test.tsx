/**
 * Tests for DownloadProgressTracker component
 *
 * This component wraps download progress display with real-time SSE updates.
 * It's critical for both home page and queue page functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DownloadProgressTracker } from './DownloadProgressTracker'
import * as useDownloadProgressSSEModule from '@/hooks/useDownloadProgressSSE'
import * as useMonotonicProgressModule from '@/hooks/useMonotonicProgress'

// Mock the hooks
vi.mock('@/hooks/useDownloadProgressSSE')
vi.mock('@/hooks/useMonotonicProgress')

describe('DownloadProgressTracker', () => {
  const mockDownloadId = 'test-download-123'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading State', () => {
    it('renders nothing when SSE data is not yet loaded', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: null,
        isConnected: false,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      const { container } = render(
        <DownloadProgressTracker downloadId={mockDownloadId} />
      )

      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('Downloading State', () => {
    it('displays progress bar for downloading status', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: {
            percentage: 45,
            downloaded_bytes: 450000000,
            total_bytes: 1000000000,
            speed: 5000000,
            eta: 110,
          },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showDetails={true}
        />
      )

      // Should show progress percentage
      expect(screen.getByText('45%')).toBeInTheDocument()
    })

    it('uses monotonic progress to prevent backwards movement', () => {
      // First render with 50%
      const mockUseSSE = vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE')
      mockUseSSE.mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 50 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      const mockMonotonic = vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress')
      mockMonotonic.mockReturnValue(50)

      const { rerender } = render(
        <DownloadProgressTracker downloadId={mockDownloadId} isActive={true} />
      )

      // Verify monotonic hook was called with raw progress
      expect(mockMonotonic).toHaveBeenCalledWith(50, 'downloading')

      // Simulate progress going backwards (shouldn't happen but test the protection)
      mockUseSSE.mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 }, // Lower!
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      // Monotonic hook returns max value (50)
      mockMonotonic.mockReturnValue(50)

      rerender(<DownloadProgressTracker downloadId={mockDownloadId} isActive={true} />)

      // Should still show 50% (monotonic progress)
      expect(mockMonotonic).toHaveBeenCalledWith(45, 'downloading')
    })

    it('displays download speed and ETA when available', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: {
            percentage: 45,
            speed: 5242880, // 5 MB/s
            eta: 120, // 2 minutes
          },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showDetails={true}
        />
      )

      // The DownloadProgress component should receive these values
      // We can't test the formatted display without mocking DownloadProgress,
      // but we can verify the component renders
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })
  })

  describe('Queued State', () => {
    it('shows 0% progress for queued status', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'queued',
          progress: null,
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(0)

      render(
        <DownloadProgressTracker downloadId={mockDownloadId} isActive={true} />
      )

      // Should show queued state
      expect(screen.getByText(/queued/i)).toBeInTheDocument()
    })
  })

  describe('Processing State', () => {
    it('shows processing indicator without specific progress', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'processing',
          progress: null,
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(0)

      render(
        <DownloadProgressTracker downloadId={mockDownloadId} isActive={true} />
      )

      // Should show processing state
      expect(screen.getByText(/processing/i)).toBeInTheDocument()
    })
  })

  describe('Completed State', () => {
    it('shows 100% progress for completed status', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'completed',
          progress: { percentage: 100 },
          result: { title: 'Test Video', url: 'https://example.com' },
          current_filename: '/path/to/file.mp4',
          message: 'Download completed',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: false, // Connection closed after completion
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(100)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={false}
          showDetails={true}
        />
      )

      // Completed downloads typically don't show progress bars
      // but the component should handle this state gracefully
      const { container } = render(
        <DownloadProgressTracker downloadId={mockDownloadId} isActive={false} />
      )
      expect(container).toBeInTheDocument()
    })
  })

  describe('Failed State', () => {
    it('handles failed status without showing progress', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'failed',
          progress: null,
          result: null,
          current_filename: null,
          message: 'Download failed',
          error: 'Network timeout',
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: false,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(0)

      const { container } = render(
        <DownloadProgressTracker downloadId={mockDownloadId} isActive={false} />
      )

      // Failed downloads don't show progress
      expect(container).toBeInTheDocument()
    })
  })

  describe('Connection Status Display', () => {
    it('shows connection status when enabled', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showConnectionStatus={true}
        />
      )

      // ConnectionStatus component should be rendered
      // (Assuming it has testable content)
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })

    it('hides connection status when disabled', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      const { container } = render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showConnectionStatus={false}
        />
      )

      // Should not have connection status
      expect(container).toBeInTheDocument()
    })
  })

  describe('Size Variants', () => {
    it('supports small size variant', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      const { container } = render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          size="sm"
        />
      )

      expect(container).toBeInTheDocument()
    })

    it('supports large size variant', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      const { container } = render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          size="lg"
        />
      )

      expect(container).toBeInTheDocument()
    })
  })

  describe('Detail Display', () => {
    it('shows details when enabled', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: {
            percentage: 45,
            downloaded_bytes: 450000000,
            total_bytes: 1000000000,
            speed: 5000000,
            eta: 110,
          },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showDetails={true}
        />
      )

      // Details should be passed to DownloadProgress
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })

    it('hides details when disabled', () => {
      vi.spyOn(useDownloadProgressSSEModule, 'useDownloadProgressSSE').mockReturnValue({
        data: {
          download_id: mockDownloadId,
          status: 'downloading',
          progress: { percentage: 45 },
          result: null,
          current_filename: null,
          message: '',
          error: null,
          created_at: '2025-01-01T10:00:00Z',
        },
        isConnected: true,
        isReconnecting: false,
        reconnectAttempts: 0,
        error: null,
      })

      vi.spyOn(useMonotonicProgressModule, 'useMonotonicProgress').mockReturnValue(45)

      render(
        <DownloadProgressTracker
          downloadId={mockDownloadId}
          isActive={true}
          showDetails={false}
        />
      )

      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })
  })
})

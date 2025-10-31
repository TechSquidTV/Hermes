/**
 * Shared component for tracking download progress with real-time SSE updates.
 *
 * This component wraps the download progress display with live SSE connection
 * for real-time updates. It handles connection status, monotonic progress,
 * and proper progress display for all download states.
 *
 * Used by both the home page (TrackedTask) and queue page (QueueCard) to ensure
 * consistent real-time updates across the app.
 */

import { useDownloadProgressSSE } from '@/hooks/useDownloadProgressSSE'
import { useMonotonicProgress } from '@/hooks/useMonotonicProgress'
import { DownloadProgress } from '@/components/ui/download-progress'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'

interface DownloadProgressTrackerProps {
  downloadId: string
  /** Whether this download is in an active state (downloading/processing) */
  isActive?: boolean
  /** Show connection status indicator */
  showConnectionStatus?: boolean
  /** Size variant for the progress display */
  size?: 'sm' | 'default' | 'lg'
  /** Show detailed progress information (speed, ETA, etc) */
  showDetails?: boolean
  /** Additional CSS classes */
  className?: string
}

/**
 * Tracks and displays real-time download progress using SSE.
 *
 * Automatically manages:
 * - SSE connection lifecycle
 * - Monotonic progress (prevents backwards movement)
 * - Connection status display
 * - Progress state transitions
 *
 * @example
 * ```tsx
 * <DownloadProgressTracker
 *   downloadId="abc-123"
 *   isActive={status === 'downloading'}
 *   showConnectionStatus={true}
 * />
 * ```
 */
export function DownloadProgressTracker({
  downloadId,
  isActive = true,
  showConnectionStatus = false,
  size = 'default',
  showDetails = true,
  className
}: DownloadProgressTrackerProps) {
  // Use SSE for real-time updates
  const {
    data: downloadStatus,
    isConnected,
    isReconnecting,
    reconnectAttempts
  } = useDownloadProgressSSE(downloadId)

  // Calculate progress percentage from SSE data
  const rawProgress = downloadStatus?.progress?.percentage ?? null
  const status = downloadStatus?.status

  // Track maximum progress to prevent jittery backwards movement
  const maxProgress = useMonotonicProgress(rawProgress, status)

  // Use maxProgress for display, ensuring it never goes backwards
  // Only apply monotonic progress for downloading/processing states
  const progressPercentage =
    status === 'completed' ? 100
    : status === 'failed' ? null
    : status === 'queued' ? 0
    : maxProgress > 0 ? maxProgress
    : null

  // Helper to extract numeric values from progress object
  const getProgressValue = (key: string): number | undefined => {
    if (!downloadStatus?.progress || typeof downloadStatus.progress !== 'object') {
      return undefined
    }
    const value = downloadStatus.progress[key as keyof typeof downloadStatus.progress]
    return typeof value === 'number' ? value : undefined
  }

  if (!downloadStatus) {
    // Still loading SSE connection
    return null
  }

  return (
    <div className={className}>
      {/* Connection Status (optional) */}
      {showConnectionStatus && isActive && (
        <ConnectionStatus
          isConnected={isConnected}
          isReconnecting={isReconnecting}
          reconnectAttempts={reconnectAttempts}
          className="mb-2"
        />
      )}

      {/* Progress Display */}
      <DownloadProgress
        progress={progressPercentage ?? undefined}
        status={status || 'unknown'}
        downloadedBytes={getProgressValue('downloaded_bytes')}
        totalBytes={getProgressValue('total_bytes')}
        speed={getProgressValue('speed')}
        estimatedTimeRemaining={getProgressValue('eta')}
        size={size}
        showDetails={showDetails}
      />
    </div>
  )
}

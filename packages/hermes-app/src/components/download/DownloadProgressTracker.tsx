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
import { Button } from '@/components/ui/button'

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
  showConnectionStatus = true,
  size = 'default',
  showDetails = true,
  className,
}: DownloadProgressTrackerProps) {
  const progress = useDownloadProgressSSE(downloadId, isActive)
  return (
    <DownloadProgressDisplay
      downloadId={downloadId}
      isActive={isActive}
      showConnectionStatus={showConnectionStatus}
      size={size}
      showDetails={showDetails}
      className={className}
      progress={progress}
    />
  )
}

export function DownloadProgressDisplay({
  downloadId,
  isActive = true,
  showConnectionStatus = true,
  size = 'default',
  showDetails = true,
  className,
  progress: live,
}: DownloadProgressTrackerProps & { progress: ReturnType<typeof useDownloadProgressSSE> }) {
  const { data: downloadStatus, isConnected, isReconnecting, reconnectAttempts, reconnect } = live

  // Calculate progress percentage from SSE data
  const rawProgress = downloadStatus?.progress?.percentage ?? null
  const status = downloadStatus?.status

  // Track maximum progress to prevent jittery backwards movement
  const maxProgress = useMonotonicProgress(rawProgress, status, downloadId)

  // Use maxProgress for display, ensuring it never goes backwards
  // Only apply monotonic progress for downloading/processing states
  const progressPercentage =
    status === 'completed'
      ? 100
      : status === 'failed'
        ? null
        : status === 'pending'
          ? 0
          : maxProgress > 0
            ? maxProgress
            : null

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

      {showConnectionStatus && isActive && !isConnected && (
        <Button variant="outline" size="sm" onClick={reconnect}>
          Reconnect live updates
        </Button>
      )}

      {/* Progress Display */}
      {downloadStatus && (
        <DownloadProgress
          progress={progressPercentage ?? undefined}
          status={status || 'unknown'}
          downloadedBytes={downloadStatus.progress?.downloadedBytes ?? undefined}
          totalBytes={downloadStatus.progress?.totalBytes ?? undefined}
          speed={downloadStatus.progress?.speed ?? undefined}
          estimatedTimeRemaining={downloadStatus.progress?.eta ?? undefined}
          size={size}
          showDetails={showDetails}
        />
      )}
    </div>
  )
}

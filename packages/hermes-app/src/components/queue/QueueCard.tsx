import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/animate-ui/components/radix/checkbox'
import {
  Download,
  Loader2,
  RefreshCw,
  Trash2,
  X
} from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import { useCancelDownload, useDownloadById } from '@/hooks/useDownloadActions'
import { StatusBadge } from '@/components/ui/status-badge'
import { DownloadProgress } from '@/components/ui/download-progress'
import { DownloadProgressTracker } from '@/components/download/DownloadProgressTracker'
import { formatFileSize } from '@/lib/utils'
import { useConfirmation } from '@/hooks/useConfirmation'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Blur } from '@/components/animate-ui/primitives/effects/blur'
import { memo, useState } from 'react'
import type { DownloadStatus } from '@/types'
import { isActiveDownloadStatus } from '@/lib/queueData'
import { invalidateQueueQueries } from '@/lib/queryClient'

interface QueueCardProps {
  download: DownloadStatus
  isSelectable?: boolean
  isSelected?: boolean
  onToggleSelect?: (downloadId: string) => void
}

export const QueueCard = memo(function QueueCard({ download, isSelectable = false, isSelected = false, onToggleSelect }: QueueCardProps) {
  const queryClient = useQueryClient()
  const { isOpen, title, description, confirmText, cancelText, variant, showConfirmation, hideConfirmation, confirm } = useConfirmation()
  const [isDismissing, setIsDismissing] = useState(false)
  const downloadFile = useDownloadById()
  const cancelDownload = useCancelDownload()

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (filePath: string) => apiClient.deleteFiles([filePath]),
    onMutate: () => {
      // Start the animation immediately when delete is initiated
      setIsDismissing(true)
    },
    onSuccess: (data) => {
      setIsDismissing(false)
      if (data.deletedFiles > 0) toast.success(`File deleted! Freed ${formatFileSize(data.totalFreedSpace)}`)
      else toast.error(data.failedDeletions?.[0] || 'File was not deleted')
      invalidateQueueQueries(queryClient, { includeFiles: true })
    },
    onError: (error) => {
      setIsDismissing(false) // Reset animation state on error
      toast.error(`Failed to delete file: ${error.message}`)
    },
  })

  const handleDownloadFile = (filePath: string | null | undefined, title: string) => {
    void downloadFile.start(download.downloadId, filePath, title)
  }

  // Delete file handler
  const handleDeleteFile = (filePath: string | null | undefined, title: string) => {
    if (!filePath) {
      toast.error('File path not available')
      return
    }

    showConfirmation({
      title: 'Delete File',
      description: `Are you sure you want to delete "${title}"? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      variant: 'destructive',
      onConfirm: () => deleteMutation.mutate(filePath),
    })
  }

  // Retry download handler (placeholder for now)
  const handleRetryDownload = () => {
    toast.info('Retry functionality coming soon!')
  }

  // Get status-based label
  const getTimestamp = () => {
    // For active downloads, show current status
    if (isActiveDownloadStatus(download.status)) {
      return 'Processing...'
    }

    // For completed downloads, show completion status
    if (download.status === 'completed') {
      return 'Completed'
    }

    // For failed downloads, show error status
    if (download.status === 'failed') {
      return 'Failed'
    }

    return download.status === 'cancelled' ? 'Cancelled' : 'Unknown'
  }

  return (
    <Blur
      initialBlur={isDismissing ? 0 : 10}
      blur={isDismissing ? 10 : 0}
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-md border hover:border-primary/50 transition-all ${isDismissing ? 'pointer-events-none' : ''}`}
    >
      {isSelectable && (
        <div className="flex items-center pr-2">
          <Checkbox
            aria-label={`Select ${download.result?.title || download.downloadId}`}
            checked={isSelected}
            onCheckedChange={() => onToggleSelect?.(download.downloadId)}
            variant="default"
            size="default"
          />
        </div>
      )}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          {download.result?.thumbnailUrl && (
            <img
              src={download.result.thumbnailUrl}
              alt={download.result.title || 'Video thumbnail'}
              className="w-12 h-8 object-cover rounded shrink-0"
              onError={(e) => {
                // Hide thumbnail if it fails to load
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          )}
          <p className="text-sm font-medium truncate">
            {(() => {
              const result = download.result
              return result?.title || `Download ${download.downloadId}`
            })()}
          </p>
        </div>

        <p className="text-xs text-muted-foreground truncate">
          {(() => {
            const result = download.result
            return result?.url || 'Processing...'
          })()}
        </p>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{getTimestamp()}</span>
          {(() => {
            const result = download.result
            return result?.fileSize && <span>• {formatFileSize(result.fileSize)}</span>
          })()}
          {(() => {
            const result = download.result
            return result?.extractor && <span>• {result.extractor}</span>
          })()}
        </div>

        {/* Use real-time SSE progress for active downloads, static display for completed/failed */}
        {(isActiveDownloadStatus(download.status)) ? (
          <DownloadProgressTracker
            downloadId={download.downloadId}
            isActive={true}
            showConnectionStatus={true}
            size="default"
            showDetails={true}
          />
        ) : (
          <DownloadProgress
            progress={download.progress?.percentage ?? undefined}
            status={download.status}
            downloadedBytes={download.progress?.downloadedBytes ?? undefined}
            totalBytes={download.progress?.totalBytes ?? undefined}
            speed={download.progress?.speed ?? undefined}
            estimatedTimeRemaining={download.progress?.eta ?? undefined}
            showDetails={true}
          />
        )}

        {download.error && (
          <p className="text-xs text-destructive wrap-break-word">
            {download.error}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between sm:flex-col sm:items-end gap-2 sm:gap-1">
        <StatusBadge status={download.status} size="sm" />

        <div className="flex gap-1">
          {download.status === 'completed' && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title="Download File"
                aria-label="Download File"
                onClick={() => {
                  const result = download.result
                  handleDownloadFile(download.currentFilename, result?.title || 'download')
                }}
              >
                <Download className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                title="Delete"
                aria-label="Delete"
                onClick={() => {
                  const result = download.result
                  handleDeleteFile(download.currentFilename, result?.title || 'download')
                }}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </Button>
            </>
          )}

          {download.status === 'failed' && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              title="Retry Download"
                aria-label="Retry Download"
              onClick={handleRetryDownload}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}

          {(isActiveDownloadStatus(download.status)) && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              title="Cancel Download"
                aria-label="Cancel Download"
              onClick={() => cancelDownload.mutate(download.downloadId)}
              disabled={cancelDownload.isPending}
            >
              {cancelDownload.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <X className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </div>

      <ConfirmationDialog
        isOpen={isOpen}
        onClose={hideConfirmation}
        onConfirm={confirm}
        title={title || 'Are you sure?'}
        description={description || 'This action cannot be undone.'}
        confirmText={confirmText || 'Confirm'}
        cancelText={cancelText || 'Cancel'}
        variant={variant || 'default'}
      />
    </Blur>
  )
})

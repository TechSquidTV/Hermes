import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/animate-ui/primitives/radix/checkbox'
import {
  Download,
  Trash2,
  Loader2,
  RefreshCw,
  X
} from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { TokenStorage } from '@/utils/tokenStorage'
import { toast } from 'sonner'
import { StatusBadge } from '@/components/ui/status-badge'
import { DownloadProgress } from '@/components/ui/download-progress'
import { formatFileSize } from '@/lib/utils'
import { useConfirmation } from '@/hooks/useConfirmation'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { Blur } from '@/components/animate-ui/primitives/effects/blur'
import { useState } from 'react'
import type { DownloadStatus, DownloadResult } from '@/types'

// Type guard to check if result is a proper DownloadResult
const isDownloadResult = (result: unknown): result is DownloadResult => {
  return typeof result === 'object' && result !== null && ('url' in result || 'title' in result || 'extractor' in result)
}

interface QueueCardProps {
  download: DownloadStatus
  isSelectable?: boolean
  isSelected?: boolean
  onToggleSelect?: (downloadId: string) => void
}

export function QueueCard({ download, isSelectable = false, isSelected = false, onToggleSelect }: QueueCardProps) {
  const queryClient = useQueryClient()
  const { isOpen, title, description, confirmText, cancelText, variant, showConfirmation, hideConfirmation, confirm } = useConfirmation()
  const [isDismissing, setIsDismissing] = useState(false)

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (filePath: string) => apiClient.deleteFiles([filePath]),
    onMutate: () => {
      // Start the animation immediately when delete is initiated
      setIsDismissing(true)
    },
    onSuccess: (data) => {
      // Wait for animation to complete before invalidating queries
      setTimeout(() => {
        if (data.deleted_files > 0) {
          toast.success(`File deleted! Freed ${(data.total_freed_space / 1024 / 1024).toFixed(2)} MB`)
        }
        // Invalidate all queue-related queries to ensure UI updates
        // Invalidate queue queries with different filter combinations
        queryClient.invalidateQueries({ queryKey: ['queue'], exact: false })
        queryClient.invalidateQueries({ queryKey: ['queue', 'active'], exact: false })
        queryClient.invalidateQueries({ queryKey: ['queue', 'history'], exact: false })
        queryClient.invalidateQueries({ queryKey: ['queue', 'all'], exact: false })
        queryClient.invalidateQueries({ queryKey: ['queueStats'], exact: false })
        queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'], exact: false })
        // Also invalidate files list to keep it in sync
        queryClient.invalidateQueries({ queryKey: ['files'], exact: false })
      }, 600) // Match animation duration
    },
    onError: (error) => {
      setIsDismissing(false) // Reset animation state on error
      toast.error(`Failed to delete file: ${error.message}`)
    },
  })

  // Download file handler
  const handleDownloadFile = async (filePath: string | null | undefined, title: string) => {
    if (!filePath) {
      toast.error('File path not available')
      return
    }

    try {
      const token = TokenStorage.getAccessToken()
      if (!token) {
        toast.error('Authentication required. Please log in again.')
        return
      }

      const url = apiClient.getDownloadFileUrl(filePath)
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          toast.error('Authentication failed. Please log in again.')
          TokenStorage.clearTokens()
          return
        }
        throw new Error(`Download failed: ${response.statusText}`)
      }

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)

      // Extract filename from filePath if available, otherwise use title
      let filename = title || 'download'
      if (filePath) {
        const pathParts = filePath.split('/')
        const fullFilename = pathParts[pathParts.length - 1]
        // Use the actual filename from the path if it has an extension
        if (fullFilename && fullFilename.includes('.')) {
          filename = fullFilename
        }
      }

      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)

      toast.success('Download started!')
    } catch (error) {
      toast.error(`Failed to download: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
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
    if (download.status === 'downloading' || download.status === 'processing' || download.status === 'queued') {
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

    return 'Unknown'
  }

  // Helper function to safely extract progress values
  const getProgressValue = (progressObj: { [key: string]: unknown } | null | undefined, key: string): number | undefined => {
    if (!progressObj || typeof progressObj !== 'object') return undefined
    const value = progressObj[key]
    return typeof value === 'number' ? value : undefined
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
            checked={isSelected}
            onCheckedChange={() => onToggleSelect?.(download.download_id)}
            className="mr-2"
          />
        </div>
      )}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          {isDownloadResult(download.result) && download.result.thumbnail_url && (
            <img
              src={download.result.thumbnail_url}
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
              const result = isDownloadResult(download.result) ? download.result : undefined
              return result?.title || `Download ${download.download_id}`
            })()}
          </p>
        </div>

        <p className="text-xs text-muted-foreground truncate">
          {(() => {
            const result = isDownloadResult(download.result) ? download.result : undefined
            return result?.url || 'Processing...'
          })()}
        </p>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{getTimestamp()}</span>
          {(() => {
            const result = isDownloadResult(download.result) ? download.result : undefined
            return result?.file_size && <span>• {formatFileSize(result.file_size)}</span>
          })()}
          {(() => {
            const result = isDownloadResult(download.result) ? download.result : undefined
            return result?.extractor && <span>• {result.extractor}</span>
          })()}
        </div>

        <DownloadProgress
          progress={
            (() => {
              const progressObj = download.progress as { [key: string]: unknown } | null | undefined
              if (!progressObj || typeof progressObj !== 'object') return undefined

              const downloaded = getProgressValue(progressObj, 'downloaded_bytes') ||
                               getProgressValue(progressObj, 'downloaded') ||
                               getProgressValue(progressObj, 'current') || 0
              const total = getProgressValue(progressObj, 'total_bytes') ||
                           getProgressValue(progressObj, 'total') ||
                           getProgressValue(progressObj, 'size') || 0

              if (downloaded && total && total > 0) {
                return (downloaded / total) * 100
              }
              return undefined
            })()
          }
          status={download.status}
          downloadedBytes={getProgressValue(download.progress as { [key: string]: unknown } | null | undefined, 'downloaded_bytes')}
          totalBytes={getProgressValue(download.progress as { [key: string]: unknown } | null | undefined, 'total_bytes')}
          speed={getProgressValue(download.progress as { [key: string]: unknown } | null | undefined, 'speed')}
          showDetails={true}
        />

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
                onClick={() => {
                  const result = isDownloadResult(download.result) ? download.result : undefined
                  handleDownloadFile(download.current_filename, result?.title || 'download')
                }}
              >
                <Download className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                title="Delete"
                onClick={() => {
                  const result = isDownloadResult(download.result) ? download.result : undefined
                  handleDeleteFile(download.current_filename, result?.title || 'download')
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
              onClick={handleRetryDownload}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}

          {(download.status === 'downloading' || download.status === 'queued') && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              title="Cancel Download"
              onClick={() => toast.info('Cancel functionality coming soon!')}
            >
              <X className="h-4 w-4" />
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
}


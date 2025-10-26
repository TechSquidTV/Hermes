import { Progress } from '@/components/ui/progress'
import { Loader2 } from 'lucide-react'
import { formatTimeRemaining, formatFileSize } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface DownloadProgressProps {
  progress?: number
  status: string
  estimatedTimeRemaining?: number
  downloadedBytes?: number
  totalBytes?: number
  speed?: number
  size?: 'sm' | 'default' | 'lg'
  showDetails?: boolean
  className?: string
}

export function DownloadProgress({
  progress,
  status,
  estimatedTimeRemaining,
  downloadedBytes,
  totalBytes,
  speed,
  size = 'default',
  showDetails = true,
  className
}: DownloadProgressProps) {
  const isIndeterminate = status === 'queued' || status === 'processing'
  const isDownloading = status === 'downloading' && typeof progress === 'number'

  if (isIndeterminate) {
    return (
      <div className={cn('flex items-center gap-2 text-sm text-muted-foreground', className)}>
        <Loader2 className={cn(
          'animate-spin',
          size === 'sm' && 'h-3 w-3',
          size === 'default' && 'h-4 w-4',
          size === 'lg' && 'h-5 w-5'
        )} />
        <span className="capitalize">{status}...</span>
      </div>
    )
  }

  if (isDownloading && progress !== undefined) {
    return (
      <div className={cn('space-y-1', className)}>
        <Progress
          value={progress}
          className={cn(
            size === 'sm' && 'h-1',
            size === 'default' && 'h-2',
            size === 'lg' && 'h-3'
          )}
        />
        {showDetails && (
          <div className="flex justify-between items-center text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span>{Math.round(progress)}%</span>
              {downloadedBytes && totalBytes && (
                <span>
                  {formatFileSize(downloadedBytes)} / {formatFileSize(totalBytes)}
                </span>
              )}
              {speed && (
                <span>{formatFileSize(speed)}/s</span>
              )}
            </div>
            {estimatedTimeRemaining && (
              <span>{formatTimeRemaining(estimatedTimeRemaining)} left</span>
            )}
          </div>
        )}
      </div>
    )
  }

  return null
}

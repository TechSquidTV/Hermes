import { Progress } from '@/components/ui/progress'
import { Loader2 } from 'lucide-react'

interface QueueProgressProps {
  progress?: number
  status: string
  estimatedTimeRemaining?: number
}

export function QueueProgress({
  progress,
  status,
  estimatedTimeRemaining,
}: QueueProgressProps) {
  // Format time remaining
  const formatTimeRemaining = (seconds: number) => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`
    }
    if (seconds < 3600) {
      return `${Math.round(seconds / 60)}m`
    }
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
  }

  // Indeterminate progress for certain statuses
  if (status === 'queued' || status === 'processing') {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="capitalize">{status}...</span>
      </div>
    )
  }

  if (status === 'downloading' && typeof progress === 'number') {
    return (
      <div className="space-y-1">
        <Progress value={progress} className="h-2" />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{Math.round(progress)}%</span>
          {estimatedTimeRemaining && (
            <span>{formatTimeRemaining(estimatedTimeRemaining)} left</span>
          )}
        </div>
      </div>
    )
  }

  return null
}


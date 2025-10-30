import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Keyboard, X, Download, AlertCircle } from 'lucide-react'
import { useDownloadProgressSSE } from '@/hooks/useDownloadProgressSSE'
import { ConnectionStatus } from '@/components/ui/ConnectionStatus'
import { UrlInput } from '@/components/forms/UrlInput'
import { KeyboardShortcutsHelp } from '@/components/ui/keyboard-shortcuts-help'
import { useState, useEffect, useCallback } from 'react'
import { useDownloadFile } from '@/hooks/useDownloadActions'
import { Blur } from '@/components/animate-ui/primitives/effects/blur'
import { taskTracker } from '@/lib/taskTracking'
import type { DownloadResult } from '@/types'

// Type guard to check if result has the expected download result properties
const hasDownloadResult = (result: unknown): result is DownloadResult => {
  return result !== null && typeof result === 'object' && ('title' in result || 'url' in result)
}

// Component to track a single download task
interface TrackedTaskProps {
  downloadId: string
  onRemove: (downloadId: string) => void
  isDismissing: boolean
}

function TrackedTask({ downloadId, onRemove, isDismissing }: TrackedTaskProps) {
  // Use SSE for real-time updates instead of polling
  const { data: downloadStatus, isConnected, isReconnecting, reconnectAttempts } = useDownloadProgressSSE(downloadId)

  // Track maximum progress to prevent jittery backwards movement
  const [maxProgress, setMaxProgress] = useState<number>(0)

  // Calculate progress percentage from SSE data
  const rawProgress = downloadStatus?.progress?.percentage ?? null
  const status = downloadStatus?.status

  // Update max progress when we see a higher value (only for active downloads)
  // This effect synchronizes external SSE state with React state, which is a valid use case
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (status === 'downloading' || status === 'processing') {
      if (rawProgress !== null && rawProgress !== undefined) {
        setMaxProgress(prev => Math.max(prev, rawProgress))
      }
    }
    // Reset maxProgress when download starts (transitions from queued)
    if (status === 'queued') {
      setMaxProgress(0)
    }
  }, [rawProgress, status])
  /* eslint-enable react-hooks/set-state-in-effect */

  // Use maxProgress for display, ensuring it never goes backwards
  // Only apply monotonic progress for downloading/processing states
  // Don't use maxProgress for completed/failed states to avoid showing stale progress
  const progressPercentage =
    status === 'completed' ? 100
    : status === 'failed' ? null
    : status === 'queued' ? 0
    : maxProgress > 0 ? maxProgress
    : null

  const downloadFile = useDownloadFile()

  const handleDownloadFile = (filePath: string | null | undefined, title: string, downloadId: string) => {
    if (!filePath) {
      return
    }

    downloadFile.mutate(
      { filePath, title },
      {
        onSuccess: () => {
          // Auto-dismiss task after successful download
          onRemove(downloadId)
        }
      }
    )
  }

  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'queued':
        return {
          color: 'bg-yellow-500',
          icon: '⏳',
          text: 'Queued',
          textColor: 'text-yellow-600 dark:text-yellow-400'
        }
      case 'downloading':
        return {
          color: 'bg-blue-500',
          icon: '⬇️',
          text: 'Downloading',
          textColor: 'text-blue-600 dark:text-blue-400'
        }
      case 'processing':
        return {
          color: 'bg-purple-500',
          icon: '⚙️',
          text: 'Processing',
          textColor: 'text-purple-600 dark:text-purple-400'
        }
      case 'completed':
        return {
          color: 'bg-green-500',
          icon: '✅',
          text: 'Completed',
          textColor: 'text-green-600 dark:text-green-400'
        }
      case 'failed':
        return {
          color: 'bg-red-500',
          icon: '❌',
          text: 'Failed',
          textColor: 'text-red-600 dark:text-red-400'
        }
      default:
        return {
          color: 'bg-gray-500',
          icon: '○',
          text: status,
          textColor: 'text-gray-600 dark:text-gray-400'
        }
    }
  }

  if (!downloadStatus) {
    // Task is loading
    return null
  }

  const task = downloadStatus
  const statusInfo = getStatusInfo(task.status)
  const isCompleted = task.status === 'completed'
  const isFailed = task.status === 'failed'
  const isActive = !isCompleted && !isFailed

  return (
    <Blur
      key={downloadId}
      initialBlur={isDismissing ? 0 : 10}
      blur={isDismissing ? 10 : 0}
      className={`
        flex items-center justify-between p-3 rounded-md border
        ${isCompleted ? 'border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20' : ''}
        ${isFailed ? 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20' : ''}
        ${isActive ? 'bg-card' : ''}
        ${isDismissing ? 'pointer-events-none' : ''}
      `}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <div className={`h-2 w-2 rounded-full ${statusInfo.color} ${isActive ? 'animate-pulse' : ''}`} />
          <span className={`text-xs font-medium ${statusInfo.textColor}`}>
            {statusInfo.text}
          </span>
          {/* SSE Connection Indicator (compact) */}
          {isActive && (
            <ConnectionStatus
              isConnected={isConnected}
              isReconnecting={isReconnecting}
              reconnectAttempts={reconnectAttempts}
              className="ml-auto"
            />
          )}
          <p className="text-sm font-medium truncate flex-1">
            {(() => {
              if (hasDownloadResult(task.result)) {
                return task.result.title || task.result.url || 'Processing...'
              }
              return 'Processing...'
            })()}
          </p>
        </div>

        {/* Progress Bar for Active Downloads */}
        {isActive && progressPercentage !== null && progressPercentage !== undefined && (
          <div className="space-y-1 mt-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{Math.round(progressPercentage)}%</span>
              {task.progress?.speed && (
                <span>{(task.progress.speed / 1024 / 1024).toFixed(2)} MB/s</span>
              )}
            </div>
            <Progress value={progressPercentage} className="h-2" />
          </div>
        )}

        {/* Status Info for Non-Active or No Progress */}
        {(isActive && (progressPercentage === null || progressPercentage === undefined)) && (
          <div className="text-xs text-muted-foreground mt-1">
            <span>Processing...</span>
          </div>
        )}

        {isCompleted && hasDownloadResult(task.result) && task.result.file_size && (
          <div className="text-xs text-muted-foreground mt-1">
            <span>{(Number(task.result.file_size) / 1024 / 1024).toFixed(2)} MB</span>
          </div>
        )}

        {isFailed && task.error && (
          <div className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1 mt-1">
            <AlertCircle className="h-3 w-3" />
            {task.error}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0 ml-3">
        {isCompleted && (
          <Button
            size="sm"
            onClick={() => handleDownloadFile(
              task.current_filename,
              hasDownloadResult(task.result) ? (task.result.title ?? 'download') : 'download',
              downloadId
            )}
            className="bg-green-600 hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600"
          >
            <Download className="h-4 w-4 mr-1" />
            Download
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onRemove(downloadId)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </Blur>
  )
}

function DashboardPage() {
  // Initialize state with tracked task IDs from taskTracker
  const [trackedTaskIds, setTrackedTaskIds] = useState<string[]>(() => taskTracker.getTasks())
  const [dismissingTasks, setDismissingTasks] = useState<Set<string>>(new Set())

  // Subscribe to task changes using event-driven system (no polling!)
  useEffect(() => {
    const unsubscribe = taskTracker.subscribe((taskIds) => {
      setTrackedTaskIds(taskIds)
    })

    return () => {
      unsubscribe()
    }
  }, [])

  const removeTask = useCallback((downloadId: string, withAnimation = true) => {
    if (withAnimation) {
      // Start the animation
      setDismissingTasks(prev => new Set(prev).add(downloadId))

      // After animation completes, actually remove the task
      setTimeout(() => {
        taskTracker.removeTask(downloadId)
        setDismissingTasks(prev => {
          const next = new Set(prev)
          next.delete(downloadId)
          return next
        })
      }, 600) // Match animation duration
    } else {
      taskTracker.removeTask(downloadId)
    }
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <KeyboardShortcutsHelp>
          <Button variant="outline" size="sm">
            <Keyboard className="h-4 w-4 mr-2" />
            Shortcuts
          </Button>
        </KeyboardShortcutsHelp>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Download</CardTitle>
        </CardHeader>
        <CardContent>
          <UrlInput />
        </CardContent>
      </Card>

      {/* Tasks Section - Only shows when there are tracked tasks */}
      {trackedTaskIds.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {trackedTaskIds.map((downloadId) => (
                <TrackedTask
                  key={downloadId}
                  downloadId={downloadId}
                  onRemove={removeTask}
                  isDismissing={dismissingTasks.has(downloadId)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export const Route = createFileRoute('/')({
  component: () => (
    <ProtectedRoute>
      <DashboardPage />
    </ProtectedRoute>
  ),
})

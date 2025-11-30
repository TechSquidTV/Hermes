import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Keyboard, X, Download, AlertCircle } from 'lucide-react'
import { useDownloadProgressSSE } from '@/hooks/useDownloadProgressSSE'
import { DownloadProgressTracker } from '@/components/download/DownloadProgressTracker'
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
  
  const { data: downloadStatus, isConnected, isReconnecting, reconnectAttempts } = useDownloadProgressSSE(downloadId)

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

        {/* Real-time Progress Display using shared component */}
        {isActive && (
          <DownloadProgressTracker
            downloadId={downloadId}
            isActive={true}
            showConnectionStatus={false}
            size="default"
            showDetails={true}
            className="mt-2"
          />
        )}

        {isCompleted && hasDownloadResult(task.result) && task.result.fileSize && (
          <div className="text-xs text-muted-foreground mt-1">
            <span>{(Number(task.result.fileSize) / 1024 / 1024).toFixed(2)} MB</span>
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
              task.currentFilename,
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

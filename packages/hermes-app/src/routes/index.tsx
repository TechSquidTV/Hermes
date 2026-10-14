import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertCircle, Download, Keyboard, X } from 'lucide-react'
import { useDownloadProgressSSE } from '@/hooks/useDownloadProgressSSE'
import { DownloadProgressDisplay } from '@/components/download/DownloadProgressTracker'
import { UrlInput } from '@/components/forms/UrlInput'
import { KeyboardShortcutsHelp } from '@/components/ui/keyboard-shortcuts-help'
import { useCallback, useEffect, useState } from 'react'
import { useDownloadById } from '@/hooks/useDownloadActions'
import { Blur } from '@/components/animate-ui/primitives/effects/blur'
import { taskTracker } from '@/lib/taskTracking'
import { StatusBadge } from '@/components/ui/status-badge'
import { isActiveDownloadStatus } from '@/lib/queueData'
import { formatFileSize } from '@/lib/utils'

// Component to track a single download task
interface TrackedTaskProps {
  downloadId: string
  onRemove: (downloadId: string) => void
}

function TrackedTask({ downloadId, onRemove }: TrackedTaskProps) {
  
  const progress = useDownloadProgressSSE(downloadId)
  const downloadStatus = progress.data

  const downloadFile = useDownloadById()

  const handleDownloadFile = (filePath: string | null | undefined, title: string, downloadId: string) => {
    void downloadFile.start(downloadId, filePath, title, () => onRemove(downloadId))
  }

  if (!downloadStatus) {
    // Task is loading
    return null
  }

  const task = downloadStatus
  const isCompleted = task.status === 'completed'
  const isFailed = task.status === 'failed'
  const isActive = isActiveDownloadStatus(task.status)

  return (
    <Blur
      key={downloadId}
      initialBlur={10}
      blur={0}
      className={`
        flex items-center justify-between p-3 rounded-md border
        ${isCompleted ? 'border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20' : ''}
        ${isFailed ? 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20' : ''}
        ${isActive ? 'bg-card' : ''}
      `}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <StatusBadge status={task.status} size="sm" />
          <p className="text-sm font-medium truncate flex-1">
            {(() => {
              if (task.result) {
                return task.result.title || task.result.url || 'Processing...'
              }
              return 'Processing...'
            })()}
          </p>
        </div>

        {/* Real-time Progress Display using shared component */}
        {isActive && (
          <DownloadProgressDisplay
            progress={progress}
            downloadId={downloadId}
            isActive={true}
            showConnectionStatus={true}
            size="default"
            showDetails={true}
            className="mt-2"
          />
        )}

        {isCompleted && !!task.result && task.result.fileSize && (
          <div className="text-xs text-muted-foreground mt-1">
            <span>{formatFileSize(task.result.fileSize)}</span>
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
              task.result ? (task.result.title ?? 'download') : 'download',
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
          aria-label="Dismiss download"
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

  useEffect(() => {
    const unsubscribe = taskTracker.subscribe((taskIds) => {
      setTrackedTaskIds(taskIds)
    })

    return () => {
      unsubscribe()
    }
  }, [])

  const removeTask = useCallback((downloadId: string) => {
    taskTracker.removeTask(downloadId)
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

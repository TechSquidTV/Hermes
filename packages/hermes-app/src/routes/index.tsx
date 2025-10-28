import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Keyboard, X, Download, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { UrlInput } from '@/components/forms/UrlInput'
import { DashboardSkeleton } from '@/components/loading/DashboardSkeleton'
import { ErrorDisplay } from '@/components/ui/error-display'
import { KeyboardShortcutsHelp } from '@/components/ui/keyboard-shortcuts-help'
import { useState, useEffect, useMemo } from 'react'
import { TokenStorage } from '@/utils/tokenStorage'
import { toast } from 'sonner'
import { Blur } from '@/components/animate-ui/primitives/effects/blur'
import type { components } from '@/types/api.generated'

type DownloadStatus = components["schemas"]["DownloadStatus"]

// Type guard to check if result has the expected download result properties
const hasDownloadResult = (result: unknown): result is { title: string; url?: string; file_size?: number } => {
  return result !== null && typeof result === 'object' && 'title' in result
}

function DashboardPage() {
  const [trackedTaskIds, setTrackedTaskIds] = useState<string[]>([])
  const [forceQueryEnabled, setForceQueryEnabled] = useState(false)
  const [dismissingTasks, setDismissingTasks] = useState<Set<string>>(new Set())

  // Load tracked task IDs from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem('homePageTasks')
    if (stored) {
      try {
        const ids = JSON.parse(stored)
        setTrackedTaskIds(ids)
        if (ids.length > 0) {
          setForceQueryEnabled(true)
        }
      } catch {
        setTrackedTaskIds([])
      }
    }
  }, [])

  // Poll sessionStorage for changes (in case UrlInput updates it)
  useEffect(() => {
    const interval = setInterval(() => {
      const stored = sessionStorage.getItem('homePageTasks')
      if (stored) {
        try {
          const ids = JSON.parse(stored)
          if (JSON.stringify(ids) !== JSON.stringify(trackedTaskIds)) {
            setTrackedTaskIds(ids)
            if (ids.length > 0) {
              setForceQueryEnabled(true)
            }
          }
        } catch {
          // ignore parse errors
        }
      }
    }, 500) // Check every 500ms

    return () => clearInterval(interval)
  }, [trackedTaskIds])

  // Query for queue to get task statuses
  const { data: queueData, isLoading: isLoadingQueue, error: queueError, refetch: refetchQueue } = useQuery({
    queryKey: ['recentDownloadsQueue'],
    queryFn: () => apiClient.getDownloadQueue(),
    refetchInterval: 2000,
    enabled: trackedTaskIds.length > 0 || forceQueryEnabled, // Poll if we have tasks or force enabled
  })

  // Filter to only show tracked tasks
  const tasks = useMemo(() => {
    if (!queueData?.items || trackedTaskIds.length === 0) return []
    
    return queueData.items.filter((download: DownloadStatus) =>
      trackedTaskIds.includes(download.download_id)
    )
  }, [queueData, trackedTaskIds])

  const removeTask = (downloadId: string, withAnimation = true) => {
    if (withAnimation) {
      // Start the animation
      setDismissingTasks(prev => new Set(prev).add(downloadId))
      
      // After animation completes, actually remove the task
      setTimeout(() => {
        const updated = trackedTaskIds.filter(id => id !== downloadId)
        setTrackedTaskIds(updated)
        sessionStorage.setItem('homePageTasks', JSON.stringify(updated))
        setDismissingTasks(prev => {
          const next = new Set(prev)
          next.delete(downloadId)
          return next
        })
      }, 600) // Match animation duration
    } else {
      const updated = trackedTaskIds.filter(id => id !== downloadId)
      setTrackedTaskIds(updated)
      sessionStorage.setItem('homePageTasks', JSON.stringify(updated))
    }
  }

  const clearCompletedTasks = () => {
    const activeTasks = tasks.filter((t: DownloadStatus) =>
      t.status !== 'completed' && t.status !== 'failed'
    )
    const activeIds = activeTasks.map((t: DownloadStatus) => t.download_id)
    setTrackedTaskIds(activeIds)
    sessionStorage.setItem('homePageTasks', JSON.stringify(activeIds))
    toast.success('Completed tasks cleared')
  }

  const handleDownloadFile = async (filePath: string | null | undefined, title: string, downloadId: string) => {
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
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`)
      }

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)

      let filename = title || 'download'
      if (filePath) {
        const pathParts = filePath.split('/')
        const fullFilename = pathParts[pathParts.length - 1]
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
      
      // Auto-dismiss task after successful download
      removeTask(downloadId, true)
    } catch (error) {
      toast.error(`Failed to download file: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
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

  if (isLoadingQueue && trackedTaskIds.length > 0) {
    return <DashboardSkeleton />
  }

  const hasError = queueError

  const hasCompletedOrFailed = tasks.some((t: DownloadStatus) =>
    t.status === 'completed' || t.status === 'failed'
  )

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

      {hasError && (
        <ErrorDisplay
          message="Failed to load dashboard data. Please check your connection and try again."
          onRetry={() => {
            refetchQueue()
          }}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Quick Download</CardTitle>
        </CardHeader>
        <CardContent>
          <UrlInput />
        </CardContent>
      </Card>

      {/* Tasks Section - Only shows when there are tracked tasks */}
      {tasks.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Tasks</CardTitle>
              {hasCompletedOrFailed && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearCompletedTasks}
                >
                  Clear Completed
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {tasks.map((task: DownloadStatus) => {
                const statusInfo = getStatusInfo(task.status)
                const isCompleted = task.status === 'completed'
                const isFailed = task.status === 'failed'
                const isActive = !isCompleted && !isFailed
                const isDismissing = dismissingTasks.has(task.download_id)

                return (
                  <Blur
                    key={task.download_id}
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
                        <p className="text-sm font-medium truncate flex-1">
                          {hasDownloadResult(task.result) ? task.result.title : ((task.result as any)?.url || 'Processing...')}
                        </p>
                      </div>
                      
                      {/* Progress Bar for Active Downloads */}
                      {isActive && task.progress?.percentage !== null && task.progress?.percentage !== undefined && (
                        <div className="space-y-1 mt-2">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>{Math.round(task.progress.percentage)}%</span>
                            {task.progress.speed && (
                              <span>{(task.progress.speed / 1024 / 1024).toFixed(2)} MB/s</span>
                            )}
                          </div>
                          <Progress value={task.progress.percentage} className="h-2" />
                        </div>
                      )}

                      {/* Status Info for Non-Active or No Progress */}
                      {(isActive && (task.progress?.percentage === null || task.progress?.percentage === undefined)) && (
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
                            hasDownloadResult(task.result) ? task.result.title : 'download',
                            task.download_id
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
                        onClick={() => removeTask(task.download_id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </Blur>
                )
              })}
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

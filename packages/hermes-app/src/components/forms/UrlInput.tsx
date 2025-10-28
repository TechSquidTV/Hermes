import { useState, useRef, useCallback } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, Upload, Link } from 'lucide-react'
import { apiClient } from '@/services/api/client'
import { VideoPreview } from '@/components/download/VideoPreview'
import { VideoPreviewSkeleton } from '@/components/loading/VideoPreviewSkeleton'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

export function UrlInput() {
  const [url, setUrl] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const debouncedUrl = useDebounce(url, 500)
  const queryClient = useQueryClient()


  const { data: videoInfo, isLoading, error } = useQuery({
    queryKey: ['videoInfo', debouncedUrl],
    queryFn: () => apiClient.getVideoInfo(debouncedUrl),
    enabled: debouncedUrl.length > 0 && isValidUrl(debouncedUrl),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Handle drag and drop
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      // Handle file drop (could be for batch processing later)
      toast.info('File drop detected - batch processing coming soon!')
      return
    }

    const text = e.dataTransfer.getData('text/plain')
    if (text && isValidUrl(text)) {
      setUrl(text)
      toast.success('URL detected and added!')
    }
  }, [])

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items)
    const textItem = items.find(item => item.type === 'text/plain')

    if (textItem) {
      textItem.getAsString((text) => {
        if (text && isValidUrl(text.trim())) {
          setUrl(text.trim())
          toast.success('URL pasted successfully!')
        }
      })
    }
  }, [])

  const downloadMutation = useMutation({
    mutationFn: (request: { url: string; format: string }) =>
      apiClient.startDownload({
        url: request.url,
        format: request.format,
        download_subtitles: false,
        download_thumbnail: false,
      }),
    onSuccess: (data) => {
      toast.success('Download started successfully!')
      queryClient.invalidateQueries({ queryKey: ['queueStats'] })
      queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'] })

      // Store the download ID for tracking on the home page (session only)
      if (data?.download_id) {
        const trackedTasks = JSON.parse(sessionStorage.getItem('homePageTasks') || '[]')
        trackedTasks.push(data.download_id)
        sessionStorage.setItem('homePageTasks', JSON.stringify(trackedTasks))
      }
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`)
    },
  })

  const handleDownload = async (format: string) => {
    if (!url || !format) return

    try {
      await downloadMutation.mutateAsync({ url, format })
    } catch (_error) {
      // Error is handled by the mutation
    }
  }

  return (
    <div className="space-y-4">
      {/* Enhanced input with drag and drop */}
      <Card className={cn(
        "transition-all duration-200 border-2 border-dashed",
        isDragOver
          ? "border-primary bg-primary/5 scale-[1.02]"
          : "border-muted-foreground/25 hover:border-muted-foreground/50"
      )}>
        <CardContent className="p-4">
          <div className="space-y-3">
            {/* Drag and drop area */}
            <div
              className="relative"
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <Input
                ref={inputRef}
                placeholder="Paste video URL here or drag & drop..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onPaste={handlePaste}
                className="pr-12 text-base h-12"
              />
              <div className="absolute right-0 top-0 h-full flex items-center pr-3">
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <div className="flex items-center gap-1">
                    <Upload className="h-4 w-4 text-muted-foreground" />
                    <Link className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            </div>

            {/* Mobile-friendly paste hint */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Supports YouTube, Vimeo, and many other platforms</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => inputRef.current?.focus()}
              >
                Focus
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Instructions for mobile users */}
      <div className="block sm:hidden text-center text-xs text-muted-foreground">
        💡 Tap the input above, then paste your video URL
      </div>

      {isLoading && <VideoPreviewSkeleton />}
      {videoInfo && !isLoading && (
        <VideoPreview
          info={videoInfo}
          onDownload={handleDownload}
          isDownloading={downloadMutation.isPending}
        />
      )}
      {error && !isLoading && <ErrorMessage error={error} />}
    </div>
  )
}

function ErrorMessage({ error }: { error: unknown }) {
  const errorMessage = error instanceof Error ? error.message : 'Failed to fetch video info'
  return (
    <div className="p-4 border border-destructive rounded-md text-destructive">
      <p className="text-sm">Error: {errorMessage}</p>
    </div>
  )
}

// Utility function to validate URLs
function isValidUrl(string: string) {
  try {
    new URL(string)
    return true
  } catch (_) {
    return false
  }
}

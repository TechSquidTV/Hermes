import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ButtonGroup } from '@/components/ui/button-group'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Checkbox, CheckboxIndicator } from '@/components/animate-ui/primitives/radix/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Calendar, Clock, Eye, User, Download, Settings, Loader2, Check, List, ExternalLink } from 'lucide-react'
import type { components } from '@/types/api.generated'

type VideoInfo = components["schemas"]["VideoInfo"]
type PlaylistEntry = components["schemas"]["PlaylistEntry"]
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import { cn, formatDate } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'
import { calculateProgressPercentage } from '@/lib/utils'

interface VideoPreviewProps {
  info: VideoInfo
  onDownload?: (format: string) => void
  isDownloading?: boolean
  progress?: { [key: string]: unknown } | null | undefined
}

export function VideoPreview({ info, onDownload, isDownloading, progress }: VideoPreviewProps) {
  const [selectedFormat, setSelectedFormat] = useState<string>('best')
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Calculate actual download progress from the progress object
  const downloadProgress = calculateProgressPercentage(progress) || 0
  const queryClient = useQueryClient()
  
  // Playlist-specific state
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set())
  const [visibleCount, setVisibleCount] = useState(10)
  const [searchQuery, setSearchQuery] = useState('')
  const [isBatchDownloading, setIsBatchDownloading] = useState(false)
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 })

  const isPlaylist = !!(info.playlist_count && info.playlist_count > 0)

  // Initialize all videos as selected
  useEffect(() => {
    if (isPlaylist && info.entries) {
      setSelectedVideos(new Set<string>(info.entries.map(e => e.id)))
    }
  }, [isPlaylist, info.entries])

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return 'N/A'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const handleDownload = () => {
    if (onDownload && selectedFormat) {
      onDownload(selectedFormat)
      setIsDialogOpen(false)
    }
  }

  // Search/Filter logic
  const filteredVideos = useMemo(() => {
    if (!isPlaylist || !info.entries) return []
    
    if (!searchQuery) return info.entries
    
    const query = searchQuery.toLowerCase()
    return info.entries.filter(e => 
      e.title.toLowerCase().includes(query) ||
      e.uploader?.toLowerCase().includes(query)
    )
  }, [isPlaylist, info.entries, searchQuery])

  const handlePlaylistDownload = async () => {
    if (!info.entries) return
    
    setIsBatchDownloading(true)
    
    try {
      const selectedEntries = info.entries.filter(e => selectedVideos.has(e.id))
      const urls = selectedEntries.map(e => e.url)
      
      if (urls.length === 0) {
        toast.error('No videos selected')
        setIsBatchDownloading(false)
        return
      }
      
      // Warn for very large downloads
      if (urls.length > 100) {
        const confirmed = window.confirm(`You're about to download ${urls.length} videos. This may take a long time. Continue?`)
        if (!confirmed) {
          setIsBatchDownloading(false)
          return
        }
      }
      
      // Split into batches of 50 (API limit)
      const batches: string[][] = []
      for (let i = 0; i < urls.length; i += 50) {
        batches.push(urls.slice(i, i + 50))
      }
      
      setBatchProgress({ current: 0, total: batches.length })
      
      // Queue all batches
      let successfulBatches = 0
      for (let i = 0; i < batches.length; i++) {
        try {
          setBatchProgress({ current: i + 1, total: batches.length })
          
          console.log(`Queueing batch ${i + 1}/${batches.length}:`, batches[i])
          
          const response = await apiClient.startBatchDownload({
            urls: batches[i],
            format: selectedFormat || 'best',
            download_subtitles: false,
            download_thumbnail: false,
            priority: 'normal',
          })
          
          console.log(`Batch ${i + 1} queued successfully:`, response)
          
          // Track download IDs on home page (same as single download behavior)
          if (response?.downloads && Array.isArray(response.downloads)) {
            const trackedTasks = JSON.parse(sessionStorage.getItem('homePageTasks') || '[]')
            trackedTasks.push(...response.downloads)
            sessionStorage.setItem('homePageTasks', JSON.stringify(trackedTasks))
          }
          
          successfulBatches++
          
          // Small delay between batches to avoid overwhelming the server
          if (i < batches.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 500))
          }
        } catch (batchError: unknown) {
          console.error(`Error queueing batch ${i + 1}:`, batchError)
          const errorMessage = batchError instanceof Error ? batchError.message : 'Unknown error'
          toast.error(`Failed to queue batch ${i + 1}/${batches.length}: ${errorMessage}`)
          
          // Ask user if they want to continue with remaining batches
          if (i < batches.length - 1) {
            const continueQueuing = window.confirm(
              `Batch ${i + 1} failed. Continue with remaining ${batches.length - i - 1} batches?`
            )
            if (!continueQueuing) {
              break
            }
          }
        }
      }
      
      if (successfulBatches > 0) {
        const totalQueued = successfulBatches * (batches[0]?.length || 0)
        toast.success(
          `Successfully queued ${totalQueued} video${totalQueued !== 1 ? 's' : ''} ` +
          `in ${successfulBatches} batch${successfulBatches !== 1 ? 'es' : ''}`
        )
        
        // Invalidate queries to refresh UI (same as single download behavior)
        queryClient.invalidateQueries({ queryKey: ['queueStats'] })
        queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'] })
      } else {
        toast.error('Failed to queue any batches. Please check the console for details.')
      }
      
    } catch (error: unknown) {
      console.error('Playlist download error:', error)
      const errorMessage = error instanceof Error ? error.message : error?.toString() || 'Unknown error'
      
      // Provide more helpful error messages
      if (errorMessage.includes('Failed to fetch')) {
        toast.error('Network error: Unable to reach the server. Please check if the API is running.')
      } else if (errorMessage.includes('401')) {
        toast.error('Authentication error: Please log in again.')
      } else if (errorMessage.includes('403')) {
        toast.error('Permission denied: You may not have access to batch downloads.')
      } else {
        toast.error(`Failed to queue downloads: ${errorMessage}`)
      }
    } finally {
      setIsBatchDownloading(false)
      setBatchProgress({ current: 0, total: 0 })
    }
  }

  const formatOptions = [
    { 
      value: 'best', 
      label: 'Best Quality',
      description: 'Highest available quality for both video and audio'
    },
    { 
      value: 'worst', 
      label: 'Lowest Quality',
      description: 'Smallest file size, lower quality'
    },
    { 
      value: 'bestvideo+bestaudio', 
      label: 'Best Video + Audio',
      description: 'Separate video and audio streams merged together'
    },
    { 
      value: 'bestaudio', 
      label: 'Audio Only',
      description: 'Download only the audio track'
    }
  ]

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-4">
          <img
            src={info.thumbnails?.[0]?.url || '/placeholder-video.svg'}
            alt={info.title}
            className="w-32 h-24 object-cover rounded-md"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <CardTitle className="text-lg leading-tight line-clamp-2 flex-1">
                {info.title}
              </CardTitle>
              {info.webpage_url && (
                <a
                  href={info.webpage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                  title="Open video in new tab"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              {info.uploader && (
                <div className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {info.uploader}
                </div>
              )}
              {info.upload_date && (
                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {formatDate(info.upload_date)}
                </div>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            {isPlaylist ? (
              <div className="flex items-center gap-1">
                <List className="h-4 w-4" />
                <span>{info.playlist_count} videos</span>
              </div>
            ) : (
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {formatDuration(info.duration)}
              </div>
            )}
            {!isPlaylist && (
              <div className="flex items-center gap-1">
                <Eye className="h-4 w-4" />
                {info.view_count?.toLocaleString() || 'N/A'}
              </div>
            )}
          </div>
          <Badge variant="secondary">
            {info.extractor}
          </Badge>
        </div>

        {info.description && (
          <>
            <Separator />
            <p className="text-sm text-muted-foreground line-clamp-3">
              {info.description}
            </p>
          </>
        )}

        {/* Playlist video list */}
        {isPlaylist && info.entries && info.entries.length > 0 && (
          <>
            <Separator />
            <div className="space-y-3">
              {/* Header with search and selection controls */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {selectedVideos.size} of {info.playlist_count} videos selected
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (selectedVideos.size === info.entries!.length) {
                        setSelectedVideos(new Set<string>())
                      } else {
                        setSelectedVideos(new Set<string>(info.entries!.map(e => e.id)))
                      }
                    }}
                  >
                    {selectedVideos.size === info.entries.length ? 'Deselect All' : 'Select All'}
                  </Button>
                </div>
              </div>
              
              {/* Search box */}
              {info.entries.length > 5 && (
                <Input
                  placeholder="Search videos..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-9"
                />
              )}
              
              {/* Video list */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredVideos.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    No videos match your search
                  </div>
                ) : (
                  filteredVideos.slice(0, visibleCount).map((entry: PlaylistEntry) => (
                    <div
                      key={entry.id}
                      className="flex items-center gap-3 p-2 rounded hover:bg-muted/50 transition-colors"
                    >
                      <Checkbox
                        checked={selectedVideos.has(entry.id)}
                        onCheckedChange={(checked) => {
                          const newSelected = new Set(selectedVideos)
                          if (checked) {
                            newSelected.add(entry.id)
                          } else {
                            newSelected.delete(entry.id)
                          }
                          setSelectedVideos(newSelected)
                        }}
                        className={cn(
                          "size-5 rounded border-2 transition-colors",
                          "border-input bg-background",
                          "data-[state=checked]:border-primary data-[state=checked]:bg-primary",
                          "disabled:cursor-not-allowed disabled:opacity-50"
                        )}
                      >
                        <CheckboxIndicator className="size-4 text-primary-foreground" />
                      </Checkbox>
                      {entry.thumbnail && (
                        <img
                          src={entry.thumbnail}
                          alt={entry.title}
                          className="w-16 h-12 object-cover rounded shrink-0"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <p className="text-sm font-medium truncate">{entry.title}</p>
                          <a
                            href={entry.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                            onClick={(e) => e.stopPropagation()}
                            title="Open video in new tab"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {entry.duration && <span>{formatDuration(entry.duration)}</span>}
                          {entry.uploader && <span>{entry.uploader}</span>}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {/* Load More button */}
              {visibleCount < filteredVideos.length && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setVisibleCount(prev => prev + 10)}
                  className="w-full"
                >
                  Load More ({filteredVideos.length - visibleCount} remaining)
                </Button>
              )}
            </div>
          </>
        )}

        {/* Empty playlist message */}
        {isPlaylist && (!info.entries || info.entries.length === 0) && (
          <>
            <Separator />
            <div className="text-center py-8 text-sm text-muted-foreground">
              This playlist has no videos
            </div>
          </>
        )}

        <Separator />

        {/* Format Selection with Dialog */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              <h3 className="text-lg font-medium">Download Options</h3>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  Change Format
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle>Select Download Format</DialogTitle>
                  <DialogDescription>
                    Choose the quality and format for your download
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  <ToggleGroup 
                    type="single" 
                    value={selectedFormat}
                    onValueChange={(value) => value && setSelectedFormat(value)}
                    className="grid grid-cols-1 gap-2"
                  >
                    {formatOptions.map((option) => (
                      <ToggleGroupItem 
                        key={option.value} 
                        value={option.value}
                        aria-label={option.label}
                        className="flex justify-between items-start h-auto p-4 text-left data-[state=on]:bg-primary/10 data-[state=on]:border-primary data-[state=on]:border-2"
                      >
                        <div className="flex-1">
                          <p className="font-medium">{option.label}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {option.description}
                          </p>
                        </div>
                        {selectedFormat === option.value && (
                          <Check className="h-5 w-5 text-primary ml-2" />
                        )}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </div>
                <DialogFooter>
                  <ButtonGroup>
                    <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => setIsDialogOpen(false)}>
                      Apply Selection
                    </Button>
                  </ButtonGroup>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Current Selection:</span>
              <Badge variant="secondary">
                {formatOptions.find(opt => opt.value === selectedFormat)?.label}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {formatOptions.find(opt => opt.value === selectedFormat)?.description}
            </p>
          </div>

          {isDownloading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Downloading...</span>
                <span className="font-medium">
                  {typeof downloadProgress === 'number' && !isNaN(downloadProgress) && downloadProgress > 0
                    ? `${Math.round(downloadProgress)}%`
                    : 'Processing...'}
                </span>
              </div>
              {typeof downloadProgress === 'number' && !isNaN(downloadProgress) && downloadProgress > 0 && (
                <Progress value={downloadProgress} className="h-2" />
              )}
            </div>
          )}

          <Button
            onClick={isPlaylist ? handlePlaylistDownload : handleDownload}
            className="w-full"
            disabled={
              isPlaylist 
                ? selectedVideos.size === 0 || isBatchDownloading
                : !selectedFormat || isDownloading
            }
            size="lg"
          >
            {isBatchDownloading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Queueing batch {batchProgress.current} of {batchProgress.total}...
              </>
            ) : isDownloading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                {isPlaylist 
                  ? `Download ${selectedVideos.size} Video${selectedVideos.size !== 1 ? 's' : ''}`
                  : 'Download Video'
                }
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}


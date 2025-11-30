import { useState, useCallback, useEffect } from 'react'
import { useVideoInfo } from './useVideoInfo'
import { useStartDownload } from './useDownloadActions'
import { isValidUrl } from '@/lib/utils'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'

type DownloadResponse = components["schemas"]["DownloadResponse"]

interface UseUrlProcessingOptions {
  onSuccess?: (data: DownloadResponse | undefined) => void
  onError?: (error: Error) => void
  defaultFormat?: string
}

export function useUrlProcessing(options: UseUrlProcessingOptions = {}) {
  const { onSuccess, onError, defaultFormat = 'best' } = options
  const [url, setUrl] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  const videoInfo = useVideoInfo(url)
  const downloadMutation = useStartDownload()

  const processUrl = useCallback(async (urlToProcess?: string) => {
    const targetUrl = urlToProcess || url

    if (!targetUrl.trim()) {
      toast.error('Please enter a URL')
      return
    }

    if (!isValidUrl(targetUrl)) {
      toast.error('Please enter a valid URL')
      return
    }

    setIsProcessing(true)

    try {
      await downloadMutation.mutateAsync({
        url: targetUrl,
        format: defaultFormat,
        downloadSubtitles: false,
        downloadThumbnail: false,
      })
      onSuccess?.(downloadMutation.data)
      setUrl('') // Clear URL after successful download
    } catch (error) {
      onError?.(error as Error)
    } finally {
      setIsProcessing(false)
    }
  }, [url, downloadMutation, defaultFormat, onSuccess, onError])

  const clearUrl = useCallback(() => {
    setUrl('')
    videoInfo.refetch()
  }, [videoInfo])

  const isValid = url.trim() && isValidUrl(url)
  const canProcess = isValid && !isProcessing

  return {
    url,
    setUrl,
    isValid,
    canProcess,
    isProcessing,
    videoInfo,
    processUrl,
    clearUrl,
    downloadMutation,
  }
}

// Hook for clipboard URL detection
export function useClipboardUrl() {
  const [clipboardUrl, setClipboardUrl] = useState('')

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = Array.from(e.clipboardData?.items || [])
      const textItem = items.find(item => item.type === 'text/plain')

      if (textItem) {
        textItem.getAsString((text) => {
          if (text && isValidUrl(text.trim())) {
            setClipboardUrl(text.trim())
          }
        })
      }
    }

    document.addEventListener('paste', handlePaste)
    return () => document.removeEventListener('paste', handlePaste)
  }, [])

  return clipboardUrl
}



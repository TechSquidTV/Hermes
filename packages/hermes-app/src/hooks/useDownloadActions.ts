import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'
import { invalidateQueueQueries } from '@/lib/queryClient'

type DownloadRequest = components["schemas"]["DownloadRequest"]
import { formatFileSize } from '@/lib/utils'

export function useStartDownload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: DownloadRequest) => apiClient.startDownload(request),
    onSuccess: () => {
      toast.success('Download started successfully!')
      invalidateQueueQueries(queryClient)
    },
    onError: (error) => {
      toast.error(`Failed to start download: ${error.message}`)
    },
  })
}

export function useDeleteFiles() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (filePaths: string[]) => apiClient.deleteFiles(filePaths),
    onSuccess: (data) => {
      if (data.deletedFiles > 0) {
        toast.success(`Files deleted! Freed ${formatFileSize(data.totalFreedSpace)}`)
      } else if (data.failedDeletions && data.failedDeletions.length > 0) {
        toast.error(`Failed to delete file: ${data.failedDeletions[0]}`)
      } else {
        toast.warning('File was not found or already deleted')
      }
      invalidateQueueQueries(queryClient, { includeFiles: true })
    },
    onError: (error) => {
      toast.error(`Failed to delete files: ${error.message}`)
    },
  })
}

export function useDownloadFile() {
  return useMutation({
    mutationFn: async ({ filePath, title }: { filePath: string; title: string }) => {
      if (!filePath) {
        throw new Error('File path not available')
      }

      const blob = await apiClient.downloadFile(filePath)
      const downloadUrl = window.URL.createObjectURL(blob)

      // Extract full filename from filePath if available
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

      return { success: true }
    },
    onSuccess: () => {
      toast.success('Download started!')
    },
    onError: (error) => {
      toast.error(`Failed to download file: ${error instanceof Error ? error.message : 'Unknown error'}`)
    },
  })
}

export function useCancelDownload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (downloadId: string) => apiClient.cancelDownload(downloadId),
    onSuccess: data => {
      if (data.cancelled) toast.success('Download cancelled')
      else toast.info(data.message)
      invalidateQueueQueries(queryClient)
    },
    onError: (error) => {
      toast.error(`Failed to cancel download: ${error.message}`)
    },
  })
}

export function useDownloadById() {
  const download = useDownloadFile()
  const [resolving, setResolving] = useState(false)
  const start = async (downloadId: string, filePath: string | null | undefined, title: string, onSuccess?: () => void) => {
    setResolving(true)
    let path: string
    try {
      const resolved = filePath || (await apiClient.getDownloadStatus(downloadId)).currentFilename
      if (!resolved) throw new Error('File is not available for this download')
      path = resolved
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Download failed')
      setResolving(false)
      return
    }
    try {
      await download.mutateAsync({ filePath: path, title })
      onSuccess?.()
    } catch { /* The download mutation displays its error. */ }
    finally { setResolving(false) }
  }
  return { start, isPending: resolving || download.isPending }
}

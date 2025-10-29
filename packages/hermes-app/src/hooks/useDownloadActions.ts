import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'

type DownloadRequest = components["schemas"]["DownloadRequest"]
import { TokenStorage } from '@/utils/tokenStorage'

export function useStartDownload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: DownloadRequest) => apiClient.startDownload(request),
    onSuccess: () => {
      toast.success('Download started successfully!')
      // Invalidate queue queries with different filter combinations
      queryClient.invalidateQueries({ queryKey: ['queue'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'active'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'history'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'all'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queueStats'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'], exact: false })
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
      if (data.deleted_files > 0) {
        toast.success(`Files deleted! Freed ${(data.total_freed_space / 1024 / 1024).toFixed(2)} MB`)
      } else if (data.failed_deletions && data.failed_deletions.length > 0) {
        toast.error(`Failed to delete file: ${data.failed_deletions[0]}`)
      } else {
        toast.warning('File was not found or already deleted')
      }
      // Invalidate queue queries with different filter combinations
      queryClient.invalidateQueries({ queryKey: ['queue'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'active'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'history'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queue', 'all'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queueStats'], exact: false })
      // Also invalidate files list to keep it in sync
      queryClient.invalidateQueries({ queryKey: ['files'], exact: false })
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

      const token = TokenStorage.getAccessToken()
      if (!token) {
        throw new Error('Authentication required. Please log in again.')
      }

      const url = apiClient.getDownloadFileUrl(filePath)
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`)
      }

      const blob = await response.blob()
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
    onSuccess: () => {
      toast.success('Download cancelled')
      queryClient.invalidateQueries({ queryKey: ['queue'] })
    },
    onError: (error) => {
      toast.error(`Failed to cancel download: ${error.message}`)
    },
  })
}



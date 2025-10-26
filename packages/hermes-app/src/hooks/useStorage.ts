import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'

type StorageInfo = components["schemas"]["StorageInfo"]
type CleanupRequest = components["schemas"]["CleanupRequest"]

export function useStorageInfo() {
  return useQuery({
    queryKey: ['storage', 'info'],
    queryFn: () => apiClient.getStorageInfo(),
    refetchInterval: 60000, // Refresh every minute
  })
}

export function useCleanup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CleanupRequest) => apiClient.cleanupDownloads(request),
    onSuccess: (data, variables) => {
      if (variables.dry_run) {
        toast.info(`Cleanup preview: ${data.files_previewed} files, ${data.space_freed} freed`)
      } else {
        toast.success(`Cleanup completed! ${data.files_deleted} files deleted, ${data.space_freed} freed`)
        queryClient.invalidateQueries({ queryKey: ['storage'] })
        queryClient.invalidateQueries({ queryKey: ['queue'] })
      }
    },
    onError: (error) => {
      toast.error(`Cleanup failed: ${error.message}`)
    },
  })
}

export function useStorageCalculations(storageInfo?: StorageInfo) {
  const totalSpace = storageInfo?.total_space || 0
  const usedSpace = storageInfo?.used_space || 0
  const freeSpace = totalSpace - usedSpace

  const usagePercentage = totalSpace > 0 ? (usedSpace / totalSpace) * 100 : 0

  const isLowSpace = usagePercentage > 90
  const isCriticalSpace = usagePercentage > 95

  return {
    totalSpace,
    usedSpace,
    freeSpace,
    usagePercentage,
    isLowSpace,
    isCriticalSpace,
  }
}

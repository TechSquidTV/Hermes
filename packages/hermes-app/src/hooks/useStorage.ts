import type { components } from '@/types/api.generated'

type StorageInfo = components["schemas"]["StorageInfo"]

export function useStorageCalculations(storageInfo?: StorageInfo) {
  const totalSpace = storageInfo?.totalSpace || 0
  const usedSpace = storageInfo?.usedSpace || 0
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

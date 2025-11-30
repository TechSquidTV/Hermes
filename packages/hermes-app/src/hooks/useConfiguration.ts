import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'

type ConfigurationUpdate = components["schemas"]["ConfigurationUpdate"]

// Type for the actual API response with snake_case properties
interface ConfigResponse {
  output_template: string
  default_format: string
  download_subtitles: boolean
  download_thumbnail: boolean
  max_concurrent_downloads: number
  cleanup_enabled: boolean
  cleanup_older_than_days: number
}

export function useConfiguration() {
  const queryClient = useQueryClient()

  // TODO: Replace with actual API call when backend implements it
  const config = useQuery({
    queryKey: ['settings', 'config'],
    queryFn: async () => ({
      output_template: '{title} [{quality}] {ext}',
      default_format: 'best',
      download_subtitles: false,
      download_thumbnail: false,
      max_concurrent_downloads: 3,
      cleanup_enabled: false,
      cleanup_older_than_days: 30,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const updateConfig = useMutation({
    mutationFn: async (_updates: ConfigurationUpdate) => {
      // TODO: Replace with actual API call
      toast.info('Configuration update coming soon!')
      return { success: true }
    },
    onSuccess: () => {
      toast.success('Settings updated successfully!')
      queryClient.invalidateQueries({ queryKey: ['settings', 'config'] })
    },
    onError: (error) => {
      toast.error(`Failed to update settings: ${error.message}`)
    },
  })

  const updateField = useCallback(<K extends keyof ConfigurationUpdate>(
    field: K,
    value: ConfigurationUpdate[K]
  ) => {
    updateConfig.mutate({ [field]: value })
  }, [updateConfig])

  return {
    config: config.data,
    isLoading: config.isLoading,
    error: config.error,
    updateConfig,
    updateField,
    isUpdating: updateConfig.isPending,
  }
}

// Hook for specific configuration sections
export function useMediaConfig() {
  const { config, updateField, isUpdating } = useConfiguration()
  const configData = config as ConfigResponse | undefined

  return {
    outputTemplate: configData?.output_template || '',
    defaultFormat: configData?.default_format || 'best',
    downloadSubtitles: configData?.download_subtitles || false,
    downloadThumbnail: configData?.download_thumbnail || false,
    updateOutputTemplate: (value: string) => updateField('outputTemplate', value),
    updateDefaultFormat: (value: string) => updateField('defaultFormat', value),
    updateDownloadSubtitles: (value: boolean) => updateField('downloadSubtitles', value),
    updateDownloadThumbnail: (value: boolean) => updateField('downloadThumbnail', value),
    isUpdating,
  }
}

export function useStorageConfig() {
  const { config, updateField, isUpdating } = useConfiguration()
  const configData = config as ConfigResponse | undefined

  return {
    maxConcurrentDownloads: configData?.max_concurrent_downloads || 3,
    cleanupEnabled: configData?.cleanup_enabled || false,
    cleanupOlderThanDays: configData?.cleanup_older_than_days || 30,
    updateMaxConcurrentDownloads: (value: number) => updateField('maxConcurrentDownloads', value),
    updateCleanupEnabled: (value: boolean) => updateField('cleanupEnabled', value),
    updateCleanupOlderThanDays: (value: number) => updateField('cleanupOlderThanDays', value),
    isUpdating,
  }
}

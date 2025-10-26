import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { toast } from 'sonner'
import type { components } from '@/types/api.generated'

type ConfigurationUpdate = components["schemas"]["ConfigurationUpdate"]

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

  return {
    outputTemplate: config?.output_template || '',
    defaultFormat: config?.default_format || 'best',
    downloadSubtitles: config?.download_subtitles || false,
    downloadThumbnail: config?.download_thumbnail || false,
    updateOutputTemplate: (value: string) => updateField('output_template', value),
    updateDefaultFormat: (value: string) => updateField('default_format', value),
    updateDownloadSubtitles: (value: boolean) => updateField('download_subtitles', value),
    updateDownloadThumbnail: (value: boolean) => updateField('download_thumbnail', value),
    isUpdating,
  }
}

export function useStorageConfig() {
  const { config, updateField, isUpdating } = useConfiguration()

  return {
    maxConcurrentDownloads: config?.max_concurrent_downloads || 3,
    cleanupEnabled: config?.cleanup_enabled || false,
    cleanupOlderThanDays: config?.cleanup_older_than_days || 30,
    updateMaxConcurrentDownloads: (value: number) => updateField('max_concurrent_downloads', value),
    updateCleanupEnabled: (value: boolean) => updateField('cleanup_enabled', value),
    updateCleanupOlderThanDays: (value: number) => updateField('cleanup_older_than_days', value),
    isUpdating,
  }
}

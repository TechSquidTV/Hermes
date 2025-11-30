/**
 * Hook for managing system settings.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'

export interface SystemSettings {
  allowPublicSignup: boolean
  updatedAt?: string
  updatedByUserId?: string
}

/**
 * Fetch system settings.
 */
export function useSystemSettings() {
  return useQuery<SystemSettings>({
    queryKey: ['admin', 'settings'],
    queryFn: () => apiClient.getAdminSettings(),
  })
}

/**
 * Update the signup setting.
 */
export function useUpdateSignupSetting() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (enabled: boolean) => apiClient.updateSignupSetting(enabled),
    onMutate: async (enabled) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['admin', 'settings'] })

      // Snapshot previous value
      const previousSettings = queryClient.getQueryData<SystemSettings>(['admin', 'settings'])

      // Optimistically update
      if (previousSettings) {
        queryClient.setQueryData<SystemSettings>(['admin', 'settings'], {
          ...previousSettings,
          allowPublicSignup: enabled,
        })
      }

      return { previousSettings }
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousSettings) {
        queryClient.setQueryData(['admin', 'settings'], context.previousSettings)
      }
    },
    onSuccess: () => {
      // Invalidate to refetch with server data
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] })
      // Also invalidate public config since it includes signup setting
      queryClient.invalidateQueries({ queryKey: ['config', 'public'] })
    },
  })
}


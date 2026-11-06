import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'
import { useAuth } from '@/contexts/AuthContext'
import { useAccountMutation } from './useAccountMutation'

type ApiKeyCreate = components['schemas']['ApiKeyCreate']
const apiKeysKey = (userId: string | undefined) => ['settings', 'api-keys', userId] as const

export function useApiKeys() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const queryKey = apiKeysKey(user?.id)

  const keys = useQuery({
    queryKey,
    queryFn: ({ signal }) => apiClient.getApiKeys(signal),
    enabled: !!user,
  })

  const createKey = useAccountMutation(user?.id, (request: ApiKeyCreate) => apiClient.createApiKey(request), {
    onSuccess: (data, userId) => {
      toast.success(`API key "${data.name}" created successfully!`)
      void queryClient.invalidateQueries({ queryKey: apiKeysKey(userId), exact: true })
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to create API key: ${errorMessage}`)
    },
  })

  const revokeKey = useAccountMutation(user?.id, (keyId: string) => apiClient.revokeApiKey(keyId), {
    onSuccess: (_data, userId) => {
      toast.success('API key revoked successfully!')
      void queryClient.invalidateQueries({ queryKey: apiKeysKey(userId), exact: true })
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to revoke API key: ${errorMessage}`)
    },
  })

  return {
    keys,
    createKey,
    revokeKey,
    isLoading: keys.isLoading || createKey.isPending || revokeKey.isPending,
  }
}

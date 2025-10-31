import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type ApiKeyCreate = components["schemas"]["ApiKeyCreate"]


export function useApiKeys() {
  const queryClient = useQueryClient()

  const keys = useQuery({
    queryKey: ['settings', 'api-keys'],
    queryFn: async () => {
      return await apiClient.getApiKeys()
    },
  })

  const createKey = useMutation({
    mutationFn: async (request: ApiKeyCreate) => {
      return await apiClient.createApiKey(request)
    },
    onSuccess: (data) => {
      toast.success(`API key "${data.name}" created successfully!`)
      queryClient.invalidateQueries({ queryKey: ['settings', 'api-keys'] })
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to create API key: ${errorMessage}`)
    },
  })

  const revokeKey = useMutation({
    mutationFn: async (keyId: string) => {
      return await apiClient.revokeApiKey(keyId)
    },
    onSuccess: () => {
      toast.success('API key revoked successfully!')
      queryClient.invalidateQueries({ queryKey: ['settings', 'api-keys'] })
    },
    onError: (error: unknown) => {
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

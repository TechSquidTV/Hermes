import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'
import { useAuth } from '@/contexts/AuthContext'

type ApiKeyCreate = components["schemas"]["ApiKeyCreate"]


export function useApiKeys() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const queryKey = ['settings', 'api-keys', user?.id] as const

  const keys = useQuery({
    queryKey,
    queryFn: ({ signal }) => apiClient.getApiKeys(signal),
    enabled: !!user,
  })

  const createKey = useMutation({
    mutationFn: async (request: ApiKeyCreate) => {
      return await apiClient.createApiKey(request)
    },
    onSuccess: (data) => {
      toast.success(`API key "${data.name}" created successfully!`)
      void queryClient.invalidateQueries({ queryKey, exact: true })
    },
    onError: (error) => {
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
      void queryClient.invalidateQueries({ queryKey, exact: true })
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

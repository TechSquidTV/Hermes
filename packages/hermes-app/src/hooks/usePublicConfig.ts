import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'

export function usePublicConfig() {
  return useQuery({ queryKey: ['config', 'public'], queryFn: () => apiClient.getPublicConfig(), staleTime: 30_000 })
}

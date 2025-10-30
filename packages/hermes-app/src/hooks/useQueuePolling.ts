import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type ApiStatistics = components["schemas"]["ApiStatistics"]

/**
 * Hook for polling download statistics
 * Note: Still uses polling - SSE for stats not yet implemented (Phase 4)
 */
export function useDownloadStatsPolling() {
  return useQuery<ApiStatistics>({
    queryKey: ['queue', 'stats'],
    queryFn: () => apiClient.getApiStats(),
    refetchInterval: 30000, // 30 seconds
    staleTime: 5000,
  })
}

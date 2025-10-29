import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type ApiStatistics = components["schemas"]["ApiStatistics"]

interface UseAnalyticsPollingOptions {
  period?: 'day' | 'week' | 'month' | 'year'
}

/**
 * Hook for polling analytics data (stats, timeline, etc.)
 * Simple 30-second polling for stats
 */
export function useAnalyticsPolling(options: UseAnalyticsPollingOptions = {}) {
  const { period = 'week' } = options

  const stats = useQuery<ApiStatistics>({
    queryKey: ['analytics', 'stats', period],
    queryFn: () => apiClient.getApiStats(period),
    refetchInterval: 30000, // 30 seconds
    staleTime: 10000, // 10 seconds
  })

  return {
    stats,
    history: null, // TODO: Implement when history API is available
    isLoading: stats.isLoading,
    error: stats.error,
  }
}

/**
 * Hook for polling timeline data
 */
export function useTimelinePolling(period: 'day' | 'week' | 'month' | 'year' = 'week') {
  return useQuery({
    queryKey: ['timeline', period],
    queryFn: () => apiClient.getTimelineStats(period),
    refetchInterval: 30000, // 30 seconds
    staleTime: 10000,
  })
}

/**
 * Hook for polling timeline summary data
 */
export function useTimelineSummaryPolling(period: 'day' | 'week' | 'month' | 'year' = 'week') {
  return useQuery({
    queryKey: ['timeline', 'summary', period],
    queryFn: () => apiClient.getTimelineSummary(period),
    refetchInterval: 30000, // 30 seconds
    staleTime: 10000,
  })
}

// Hook specifically for chart data transformation (no polling - pure data transformation)
export function useChartData(stats?: ApiStatistics) {
  // Transform stats for extractor pie chart
  const extractorChartData = stats?.popular_extractors?.map(extractor => ({
    name: extractor.extractor,
    value: extractor.count,
    percentage: extractor.percentage,
  })) || []

  // Transform stats for error breakdown chart
  const errorChartData = stats?.error_breakdown?.map(error => ({
    name: error.error_type,
    value: error.count,
    percentage: error.percentage,
  })) || []

  // Transform stats for time series chart (placeholder for now)
  const timeSeriesData: components["schemas"]["DailyStats"][] = []

  return {
    extractorChartData,
    errorChartData,
    timeSeriesData,
  }
}

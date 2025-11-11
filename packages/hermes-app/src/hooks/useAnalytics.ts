import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type ApiStatistics = components["schemas"]["ApiStatistics"]

interface UseAnalyticsOptions {
  period?: 'day' | 'week' | 'month' | 'year'
  historyFilters?: {
    start_date?: string
    end_date?: string
    extractor?: string
    status?: string
    limit?: number
    offset?: number
  }
}

export function useAnalytics(options: UseAnalyticsOptions = {}) {
  const { period = 'week' } = options

  const stats = useQuery({
    queryKey: ['analytics', 'stats', period],
    queryFn: () => apiClient.getApiStats(period),
  })

  return {
    stats,
    history: null, // TODO: Implement when history API is available
    isLoading: stats.isLoading,
    error: stats.error,
  }
}

// Types for the raw API response with snake_case
interface ExtractorStat {
  extractor: string
  count: number
  percentage: number
}

interface ErrorStat {
  error_type: string
  count: number
  percentage: number
}

// Hook specifically for chart data transformation
export function useChartData(stats?: ApiStatistics) {
  // Transform stats for extractor pie chart
  const extractorChartData = (stats?.popularExtractors as ExtractorStat[] | undefined)?.map((extractor) => ({
    name: extractor.extractor,
    value: extractor.count,
    percentage: extractor.percentage,
  })) || []

  // Transform stats for error breakdown chart
  const errorChartData = (stats?.errorBreakdown as ErrorStat[] | undefined)?.map((error) => ({
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

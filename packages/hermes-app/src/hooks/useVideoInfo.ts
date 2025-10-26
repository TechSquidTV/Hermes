import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api/client'
import { useDebounce } from './useDebounce'
import { isValidUrl } from '@/lib/utils'

interface UseVideoInfoOptions {
  includeFormats?: boolean
  staleTime?: number
  enabled?: boolean
}

export function useVideoInfo(
  url: string,
  options: UseVideoInfoOptions = {}
) {
  const {
    includeFormats = true,
    staleTime = 5 * 60 * 1000, // 5 minutes
    enabled = true,
  } = options

  const debouncedUrl = useDebounce(url, 500)

  return useQuery({
    queryKey: ['videoInfo', debouncedUrl, includeFormats],
    queryFn: () => apiClient.getVideoInfo(debouncedUrl, includeFormats),
    enabled: enabled && debouncedUrl.length > 0 && isValidUrl(debouncedUrl),
    staleTime,
    retry: (failureCount, error) => {
      // Don't retry on 404 or validation errors
      if (error.message?.includes('404') || error.message?.includes('400')) {
        return false
      }
      return failureCount < 2
    },
  })
}



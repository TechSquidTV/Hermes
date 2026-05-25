// React Query Client Configuration

import { QueryClient } from '@tanstack/react-query'

interface InvalidateQueueOptions {
  includeFiles?: boolean
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error instanceof Error && 'status' in error && typeof error.status === 'number') {
          if (error.status >= 400 && error.status < 500) {
            return false
          }
        }
        return failureCount < 3
      },
    },
    mutations: {
      retry: 1,
    },
  },
})

export function invalidateQueueQueries(
  client: QueryClient,
  options: InvalidateQueueOptions = {}
) {
  client.invalidateQueries({ queryKey: ['queue'], exact: false })
  client.invalidateQueries({ queryKey: ['queue', 'active'], exact: false })
  client.invalidateQueries({ queryKey: ['queue', 'history'], exact: false })
  client.invalidateQueries({ queryKey: ['queue', 'all'], exact: false })
  client.invalidateQueries({ queryKey: ['queueStats'], exact: false })
  client.invalidateQueries({ queryKey: ['recentDownloadsQueue'], exact: false })

  if (options.includeFiles) {
    client.invalidateQueries({ queryKey: ['files'], exact: false })
  }
}

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
      retry: false,
    },
  },
})

export function invalidateQueueQueries(
  client: QueryClient,
  options: InvalidateQueueOptions = {}
) {
  void client.invalidateQueries({ queryKey: ['queue'], exact: false })

  if (options.includeFiles) {
    void client.invalidateQueries({ queryKey: ['files'], exact: false })
  }
}

const scheduled = new WeakMap<QueryClient, ReturnType<typeof setTimeout>>()

/** Coalesce queue/status/stats events into one invalidation per short burst. */
export function scheduleLiveInvalidation(client: QueryClient): void {
  if (scheduled.has(client)) return
  scheduled.set(client, setTimeout(() => {
    scheduled.delete(client)
    invalidateQueueQueries(client)
    void client.invalidateQueries({ queryKey: ['analytics'], exact: false })
    void client.invalidateQueries({ queryKey: ['timeline'], exact: false })
  }, 250))
}

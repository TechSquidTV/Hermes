import { type ReactNode, createContext, useContext, useEffect, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSSE } from '@/hooks/useSSE'
import { useSSEToken } from '@/hooks/useSSEToken'
import { getApiBaseUrl } from '@/lib/config'
import { type DownloadEvent, normalizeDownloadEvent } from '@/lib/downloadEvents'
import { scheduleLiveInvalidation } from '@/lib/queryClient'
import { isActiveDownloadStatus } from '@/lib/queueData'
import type { components } from '@/types/api.generated'

type DownloadStatus = components['schemas']['DownloadStatus']
interface Connection {
  isConnected: boolean
  isReconnecting: boolean
  reconnectAttempts: number
  error: Error | null
  reconnect: () => void
}
const Context = createContext<Connection | null>(null)
const OPTIONS = { events: ['download_progress'], maxReconnectAttempts: 10 }

export function DownloadEventsProvider({
  enabled,
  children,
}: {
  enabled: boolean
  children: ReactNode
}) {
  const queryClient = useQueryClient()
  const { token, error: tokenError, retry } = useSSEToken('downloads', 600, enabled)
  const url = token ? `${getApiBaseUrl()}/events/stream?token=${encodeURIComponent(token)}` : null
  const { data, isConnected, isReconnecting, reconnectAttempts, error, reconnect } =
    useSSE<DownloadEvent>(url, {
      ...OPTIONS,
      onOpen: () => {
        if (!enabled) return
        // Pub/Sub cannot replay missed events. Reconcile observed, nonterminal
        // downloads on every open, even when their cached snapshot is fresh.
        void queryClient.refetchQueries({
          queryKey: ['download', 'progress'],
          type: 'active',
          predicate: (query) => {
            const status = query.state.data as DownloadStatus | undefined
            return !status || isActiveDownloadStatus(status.status)
          },
        })
      },
    })
  useEffect(() => {
    if (!enabled || !data?.download_id) return
    const key = ['download', 'progress', data.download_id] as const
    const previous = queryClient.getQueryData<DownloadStatus>(key)
    const status = normalizeDownloadEvent(data, previous)
    if (status) {
      // Cancel an older HTTP snapshot before applying the live event. Cancellation
      // reverts synchronously, so later events cannot be overwritten by that fetch.
      void queryClient.cancelQueries({ queryKey: key, exact: true })
      queryClient.setQueryData(key, status)
      if (['completed', 'failed', 'cancelled'].includes(status.status))
        scheduleLiveInvalidation(queryClient)
    }
  }, [enabled, data, queryClient])
  const connection = useMemo<Connection>(
    () => ({
      isConnected,
      isReconnecting,
      reconnectAttempts,
      error: tokenError ?? error,
      reconnect: () => {
        retry()
        reconnect()
      },
    }),
    [isConnected, isReconnecting, reconnectAttempts, tokenError, error, retry, reconnect]
  )
  return <Context.Provider value={connection}>{children}</Context.Provider>
}

export function useDownloadConnection(): Connection {
  const context = useContext(Context)
  if (!context) throw new Error('DownloadEventsProvider is required')
  return context
}

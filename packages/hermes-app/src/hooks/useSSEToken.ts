import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import { TokenStorage } from '@/utils/tokenStorage'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

type TokenResponse = components['schemas']['SSETokenResponse']
const BUFFER = 60_000

function renewalDelay(response: TokenResponse): number {
  return Math.max(
    1000,
    Math.min(response.ttl * 1000, Date.parse(response.expiresAt) - Date.now()) - BUFFER
  )
}

export function useSSEToken(scope: string, ttl: number, enabled = true) {
  const version = useSyncExternalStore(TokenStorage.subscribe, TokenStorage.getVersion)
  const [state, setState] = useState<{ scope: string; version: number; token: string | null; error: Error | null }>({
    scope,
    version,
    token: null,
    error: null,
  })
  const [attempt, setAttempt] = useState(0)
  const retry = useCallback(() => setAttempt((value) => value + 1), [])
  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    let failures = 0
    async function fetchToken() {
      try {
        const response = await apiClient.createSSEToken({ scope, ttl }, controller.signal)
        if (controller.signal.aborted) return
        failures = 0
        setState({ scope, version, token: response.token, error: null })
        timer = setTimeout(() => {
          void fetchToken()
        }, renewalDelay(response))
      } catch (error) {
        if (controller.signal.aborted) return
        setState((previous) => ({
          scope,
          version,
          token: previous.scope === scope && previous.version === version ? previous.token : null,
          error: error instanceof Error ? error : new Error('Live updates unavailable'),
        }))
        timer = setTimeout(
          () => {
            void fetchToken()
          },
          Math.min(1000 * 2 ** failures++, 30_000)
        )
      }
    }
    void fetchToken()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [scope, ttl, attempt, enabled, version])
  return {
    token: enabled && state.scope === scope && state.version === version ? state.token : null,
    error: state.scope === scope && state.version === version ? state.error : null,
    retry,
  }
}

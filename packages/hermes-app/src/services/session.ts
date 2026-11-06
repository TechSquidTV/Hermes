import { ApiError } from '@/lib/errors'
import { getApiBaseUrl } from '@/lib/config'
import type { components } from '@/types/api.generated'
import { TokenStorage } from '@/utils/tokenStorage'
import { checkResponse, isAuthenticationError, withRequestSignal } from './http'

type TokenResponse = components['schemas']['TokenResponse']
let pendingRefresh: { token: string; version: number; promise: Promise<TokenResponse> } | null =
  null

async function exchangeRefreshToken(refreshToken: string, version: number, sessionId: string | null): Promise<TokenResponse> {
  return withRequestSignal(undefined, 30_000, async (signal) => {
    const rotatedTokens = (): TokenResponse | null => {
      if (TokenStorage.getVersion() !== version || TokenStorage.getSessionId() !== sessionId)
        throw new DOMException('Session changed during token refresh', 'SessionChangedError')
      const currentRefresh = TokenStorage.getRefreshToken()
      if (currentRefresh === refreshToken) return null
      const accessToken = TokenStorage.getAccessToken()
      if (!sessionId || !currentRefresh || !accessToken)
        throw new DOMException('Session changed during token refresh', 'SessionChangedError')
      return { accessToken, refreshToken: currentRefresh, tokenType: 'bearer' }
    }
    const exchange = async (): Promise<TokenResponse> => {
      // A tab waiting for the origin-wide lock reuses the winner's rotation.
      const alreadyRotated = rotatedTokens()
      if (alreadyRotated) return alreadyRotated
      let response: Response
      try {
        response = await checkResponse(
          await fetch(`${getApiBaseUrl()}/auth/refresh`, {
            method: 'POST',
            signal,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refreshToken }),
          })
        )
      } catch (error) {
        // Also handle rotations from older tabs or contexts without Web Locks.
        if (isAuthenticationError(error)) {
          const current = rotatedTokens()
          if (current) return current
        }
        throw error
      }
      const tokens: TokenResponse = await response.json()
      signal.throwIfAborted()
      const current = rotatedTokens()
      if (current) return current
      TokenStorage.setTokens(tokens, false)
      return tokens
    }
    return navigator.locks
      ? navigator.locks.request('hermes-session-refresh', { signal }, exchange)
      : exchange()
  })
}

export function refreshSession(): Promise<TokenResponse> {
  const token = TokenStorage.getRefreshToken()
  if (!token) return Promise.reject(new ApiError(401, 'Authentication required'))
  const version = TokenStorage.getVersion()
  if (pendingRefresh?.token === token && pendingRefresh.version === version)
    return pendingRefresh.promise
  const promise = exchangeRefreshToken(token, version, TokenStorage.getSessionId()).finally(() => {
    if (pendingRefresh?.promise === promise) pendingRefresh = null
  })
  pendingRefresh = { token, version, promise }
  return promise
}

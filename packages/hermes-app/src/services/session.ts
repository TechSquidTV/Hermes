import { ApiError } from '@/lib/errors'
import { getApiBaseUrl } from '@/lib/config'
import type { components } from '@/types/api.generated'
import { TokenStorage } from '@/utils/tokenStorage'
import { checkResponse, isAuthenticationError, withRequestSignal } from './http'
import { SESSION_REFRESH_TIMEOUT_MS, withSessionLock } from './sessionLock'

type TokenResponse = components['schemas']['TokenResponse']
let pendingRefresh: { token: string; version: number; promise: Promise<TokenResponse> } | null =
  null

async function exchangeRefreshToken(refreshToken: string, version: number, sessionId: string | null): Promise<TokenResponse> {
  return withRequestSignal(undefined, SESSION_REFRESH_TIMEOUT_MS, async (signal) => {
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
    const exchange = async (assertCurrent: () => void): Promise<TokenResponse> => {
      // A tab waiting for the shared lease reuses the winner's rotation.
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
        // Another version of the app may already have rotated the credential.
        if (isAuthenticationError(error)) {
          const current = rotatedTokens()
          if (current) return current
        }
        throw error
      }
      const tokens: TokenResponse = await response.json()
      assertCurrent()
      const current = rotatedTokens()
      if (current) return current
      TokenStorage.setTokens(tokens, false)
      return tokens
    }
    return withSessionLock(signal, exchange)
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

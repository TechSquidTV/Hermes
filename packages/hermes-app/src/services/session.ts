import { ApiError } from '@/lib/errors'
import { getApiBaseUrl } from '@/lib/config'
import type { components } from '@/types/api.generated'
import { TokenStorage } from '@/utils/tokenStorage'
import { checkResponse, withRequestSignal } from './http'

type TokenResponse = components['schemas']['TokenResponse']
let pendingRefresh: { token: string; version: number; promise: Promise<TokenResponse> } | null =
  null

async function exchangeRefreshToken(refreshToken: string, version: number): Promise<TokenResponse> {
  return withRequestSignal(undefined, 30_000, async (signal) => {
    const response = await checkResponse(
      await fetch(`${getApiBaseUrl()}/auth/refresh`, {
        method: 'POST',
        signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      })
    )
    const tokens: TokenResponse = await response.json()
    if (TokenStorage.getRefreshToken() !== refreshToken || TokenStorage.getVersion() !== version) {
      throw new DOMException('Session changed during token refresh', 'AbortError')
    }
    TokenStorage.setTokens(tokens, false)
    return tokens
  })
}

export function refreshSession(): Promise<TokenResponse> {
  const token = TokenStorage.getRefreshToken()
  if (!token) return Promise.reject(new ApiError(401, 'Authentication required'))
  const version = TokenStorage.getVersion()
  if (pendingRefresh?.token === token && pendingRefresh.version === version)
    return pendingRefresh.promise
  const promise = exchangeRefreshToken(token, version).finally(() => {
    if (pendingRefresh?.promise === promise) pendingRefresh = null
  })
  pendingRefresh = { token, version, promise }
  return promise
}

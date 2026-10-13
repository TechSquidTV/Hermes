import { getApiBaseUrl } from '@/lib/config'
import type { components } from '@/types/api.generated'
import { TokenStorage } from '@/utils/tokenStorage'

type TokenResponse = components['schemas']['TokenResponse']

let pendingRefresh: Promise<TokenResponse> | null = null

async function exchangeRefreshToken(): Promise<TokenResponse> {
  const refreshToken = TokenStorage.getRefreshToken()
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const response = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: Token refresh failed`)
  }

  const tokens: TokenResponse = await response.json()
  // An earlier refresh response must never restore a session after logout or
  // replace credentials from a subsequent login.
  if (TokenStorage.getRefreshToken() !== refreshToken) {
    throw new Error('Session changed during token refresh')
  }
  TokenStorage.setAccessToken(tokens.accessToken, 15)
  TokenStorage.setRefreshToken(tokens.refreshToken)
  return tokens
}

export function refreshSession(): Promise<TokenResponse> {
  pendingRefresh ??= exchangeRefreshToken().finally(() => {
    pendingRefresh = null
  })
  return pendingRefresh
}

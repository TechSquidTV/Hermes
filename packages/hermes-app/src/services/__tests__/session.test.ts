import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../api/client'
import { authService } from '../auth'
import { refreshSession } from '../session'
import { TokenStorage } from '@/utils/tokenStorage'

const replacement = {
  accessToken: 'new-access',
  refreshToken: 'new-refresh',
  tokenType: 'bearer',
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((complete) => { resolve = complete })
  return { promise, resolve }
}

describe('Session refresh coordination', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    TokenStorage.setAccessToken('old-access')
    TokenStorage.setRefreshToken('old-refresh')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shares one rotation across auth and API services', async () => {
    const exchange = deferred<Response>()
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (url) => {
      if (url === '/api/v1/auth/refresh') return exchange.promise
      return TokenStorage.getAccessToken() === 'old-access'
        ? new Response('{}', { status: 401 })
        : new Response(JSON.stringify({ result: 'ok' }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const first = authService.refreshToken()
    const second = apiClient.request<{ result: string }>('/one')
    const third = apiClient.request<{ result: string }>('/two')
    await vi.waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => url === '/api/v1/auth/refresh')).toHaveLength(1))
    exchange.resolve(new Response(JSON.stringify(replacement)))
    const results = await Promise.all([first, second, third])
    expect(results).toEqual([replacement, { result: 'ok' }, { result: 'ok' }])
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/v1/auth/refresh')).toHaveLength(1)
    expect(TokenStorage.getRefreshToken()).toBe('new-refresh')
  })

  it('retries a delayed 401 with the already-refreshed access token', async () => {
    const delayed = deferred<Response>()
    let delayedCalls = 0
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (url, options) => {
      if (url === '/api/v1/auth/refresh') return new Response(JSON.stringify(replacement))
      if (url === '/api/v1/slow' && delayedCalls++ === 0) return delayed.promise
      if (new Headers(options?.headers).get('Authorization') === 'Bearer old-access') return new Response('{}', { status: 401 })
      return new Response(JSON.stringify({ result: 'ok' }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const slow = apiClient.request<{ result: string }>('/slow')
    expect(await apiClient.request<{ result: string }>('/fast')).toEqual({ result: 'ok' })
    delayed.resolve(new Response('{}', { status: 401 }))
    expect(await slow).toEqual({ result: 'ok' })
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/v1/auth/refresh')).toHaveLength(1)
  })

  it('does not restore credentials when logout happens during refresh', async () => {
    const exchange = deferred<Response>()
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockReturnValue(exchange.promise))
    const refresh = refreshSession()
    TokenStorage.clearTokens()
    const rejected = expect(refresh).rejects.toThrow('Session changed')
    exchange.resolve(new Response(JSON.stringify(replacement)))
    await rejected
    expect(TokenStorage.getAccessToken()).toBeNull()
    expect(TokenStorage.getRefreshToken()).toBeNull()
  })

  it('does not overwrite credentials from a newer login', async () => {
    const exchange = deferred<Response>()
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockReturnValue(exchange.promise))
    const refresh = refreshSession()
    TokenStorage.setAccessToken('other-access')
    TokenStorage.setRefreshToken('other-refresh')
    const rejected = expect(refresh).rejects.toThrow('Session changed')
    exchange.resolve(new Response(JSON.stringify(replacement)))
    await rejected
    expect(TokenStorage.getAccessToken()).toBe('other-access')
    expect(TokenStorage.getRefreshToken()).toBe('other-refresh')
  })

  it('allows a later refresh attempt after a failed exchange', async () => {
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('{}', { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(replacement)))
    vi.stubGlobal('fetch', fetchMock)
    await expect(refreshSession()).rejects.toThrow('503')
    expect(await refreshSession()).toEqual(replacement)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('keeps a valid session when a retried request is forbidden', async () => {
    const clear = vi.spyOn(TokenStorage, 'clearTokens')
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(replacement)))
      .mockResolvedValueOnce(new Response('{}', { status: 403, statusText: 'Forbidden' }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient.request('/admin')).rejects.toThrow('403')
    expect(clear).not.toHaveBeenCalled()
    expect(TokenStorage.getAccessToken()).toBe('new-access')
  })

  it('revokes the server session on logout even after the access token expires', async () => {
    TokenStorage.clearAccessToken()
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(replacement)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: 'Successfully logged out' })))
    vi.stubGlobal('fetch', fetchMock)
    await authService.logout()
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/refresh', '/api/v1/auth/logout'])
    expect(new Headers(fetchMock.mock.calls.at(1)?.[1]?.headers).get('Authorization')).toBe('Bearer new-access')
    expect(TokenStorage.getAccessToken()).toBeNull()
    expect(TokenStorage.getRefreshToken()).toBeNull()
  })
})

it('retains rotated credentials when the retried request loses the network', async () => {
  TokenStorage.setTokens({ accessToken: 'old', refreshToken: 'refresh' })
  vi.stubGlobal('fetch', vi.fn<typeof fetch>()
    .mockResolvedValueOnce(new Response('{}', { status: 401 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(replacement)))
    .mockRejectedValueOnce(new TypeError('Network unavailable')))
  try {
    await expect(apiClient.request('/download/one')).rejects.toThrow('Network unavailable')
    expect(TokenStorage.getRefreshToken()).toBe('new-refresh')
    expect(TokenStorage.getAccessToken()).toBe('new-access')
  } finally { vi.unstubAllGlobals() }
})

it('forwards cancellation and bounds requests with a timeout', async () => {
  TokenStorage.setTokens({ accessToken: 'access', refreshToken: 'refresh' })
  vi.useFakeTimers()
  const fetchMock = vi.fn<typeof fetch>().mockImplementation((_url, options) => new Promise((_resolve, reject) => {
    options?.signal?.addEventListener('abort', () => reject(options.signal?.reason), { once: true })
  }))
  vi.stubGlobal('fetch', fetchMock)
  try {
    const controller = new AbortController()
    const aborted = expect(apiClient.request('/slow', { signal: controller.signal })).rejects.toThrow('cancelled')
    controller.abort(new DOMException('cancelled', 'AbortError'))
    await aborted
    const timeout = expect(apiClient.request('/slow', { timeoutMs: 100 })).rejects.toThrow('Request timed out')
    await vi.advanceTimersByTimeAsync(100)
    await timeout
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
  } finally { vi.useRealTimers(); vi.unstubAllGlobals() }
})

function sessionAccess(sid: string): string {
  return `header.${btoa(JSON.stringify({ exp: Date.now() / 1000 + 900, sid }))}.signature`
}

it('serializes independent HTTP tabs and reuses the completed rotation', async () => {
  localStorage.clear()
  TokenStorage.setTokens({ accessToken: sessionAccess('family'), refreshToken: 'old-refresh' })
  vi.stubGlobal('navigator', {})
  const tokens = { accessToken: sessionAccess('family'), refreshToken: 'new-refresh', tokenType: 'bearer' }
  const exchange = deferred<Response>()
  const fetchMock = vi.fn<typeof fetch>().mockReturnValue(exchange.promise)
  vi.stubGlobal('fetch', fetchMock)
  try {
    vi.resetModules()
    const firstTab = await import('../session')
    vi.resetModules()
    const secondTab = await import('../session')
    const first = firstTab.refreshSession()
    const second = secondTab.refreshSession()
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    exchange.resolve(new Response(JSON.stringify(tokens)))
    expect(await Promise.all([first, second])).toEqual([tokens, tokens])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(TokenStorage.getRefreshToken()).toBe('new-refresh')
  } finally { vi.unstubAllGlobals(); localStorage.clear() }
})

it('uses another tab\'s same-session credentials after a late refresh rejection', async () => {
  localStorage.clear()
  TokenStorage.setTokens({ accessToken: sessionAccess('family'), refreshToken: 'old-refresh' })
  vi.stubGlobal('navigator', {})
  const winningAccess = sessionAccess('family')
  const exchange = deferred<Response>()
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (url, options) => {
    if (url === '/api/v1/auth/refresh') return exchange.promise
    return new Headers(options?.headers).get('Authorization') === 'Bearer ' + winningAccess && TokenStorage.getRefreshToken() === 'new-refresh'
      ? new Response('{"result":"ok"}')
      : new Response('{}', { status: 401 })
  })
  vi.stubGlobal('fetch', fetchMock)
  try {
    const request = apiClient.request<{ result: string }>('/auth/me')
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    localStorage.setItem('hermes_access_token', winningAccess)
    localStorage.setItem('hermes_refresh_token', 'new-refresh')
    exchange.resolve(new Response('{"detail":"Refresh token has been revoked"}', { status: 401 }))
    expect(await request).toEqual({ result: 'ok' })
    expect(TokenStorage.getRefreshToken()).toBe('new-refresh')
  } finally { vi.unstubAllGlobals(); localStorage.clear() }
})

it('does not adopt a different account even before its storage event arrives', async () => {
  localStorage.clear()
  TokenStorage.setTokens({ accessToken: sessionAccess('family-a'), refreshToken: 'old-refresh' })
  const exchange = deferred<Response>()
  vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockReturnValue(exchange.promise))
  try {
    const refresh = refreshSession()
    const rejected = expect(refresh).rejects.toThrow('Session changed')
    localStorage.setItem('hermes_access_token', sessionAccess('family-b'))
    localStorage.setItem('hermes_refresh_token', 'other-account-refresh')
    exchange.resolve(new Response('{}', { status: 401 }))
    await rejected
    expect(TokenStorage.getRefreshToken()).toBe('other-account-refresh')
  } finally { vi.unstubAllGlobals(); localStorage.clear() }
})

it('prevents a plain-HTTP losing rejection before the winning response is persisted', async () => {
  localStorage.clear()
  const expired = `header.${btoa(JSON.stringify({ exp: 1, sid: 'family' }))}.signature`
  localStorage.setItem('hermes_access_token', expired)
  localStorage.setItem('hermes_refresh_token', 'old-refresh')
  vi.stubGlobal('navigator', {})
  const exchange = deferred<Response>()
  const tokens = { accessToken: sessionAccess('family'), refreshToken: 'rotated', tokenType: 'bearer' }
  let refreshes = 0
  const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (url, options) => {
    if (url === '/api/v1/auth/refresh') {
      refreshes += 1
      return refreshes === 1 ? exchange.promise : new Response('{}', { status: 401 })
    }
    expect(new Headers(options?.headers).get('Authorization')).toBe(`Bearer ${tokens.accessToken}`)
    return new Response('{"result":"ok"}')
  })
  vi.stubGlobal('fetch', fetchMock)
  try {
    vi.resetModules()
    const winner = await import('../session')
    vi.resetModules()
    const loser = await import('../api/client')
    const first = winner.refreshSession()
    await vi.waitFor(() => expect(refreshes).toBe(1))
    const second = loser.apiClient.request<{ result: string }>('/auth/me')
    await new Promise(resolve => setTimeout(resolve, 25))
    expect(refreshes).toBe(1)
    exchange.resolve(new Response(JSON.stringify(tokens)))
    expect(await first).toEqual(tokens)
    expect(await second).toEqual({ result: 'ok' })
    expect(localStorage.getItem('hermes_refresh_token')).toBe('rotated')
  } finally { vi.unstubAllGlobals(); localStorage.clear() }
})

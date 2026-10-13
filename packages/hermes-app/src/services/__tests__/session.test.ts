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
    TokenStorage.setAccessToken('old-access', 15)
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
    TokenStorage.setAccessToken('other-access', 15)
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
    expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get('Authorization')).toBe('Bearer new-access')
    expect(TokenStorage.getAccessToken()).toBeNull()
    expect(TokenStorage.getRefreshToken()).toBeNull()
  })
})

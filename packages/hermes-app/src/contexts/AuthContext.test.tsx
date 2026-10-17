import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from '@/services/auth'
import { ApiError } from '@/lib/errors'
import { TokenStorage } from '@/utils/tokenStorage'
import type { User } from '@/types/auth'
import { AuthProvider, useAuth } from './AuthContext'
import { apiClient } from '@/services/api/client'
import { useApiKeys } from '@/hooks/useApiKeys'

vi.mock('@/services/api/client', () => ({
  apiClient: { getApiKeys: vi.fn(), createApiKey: vi.fn(), revokeApiKey: vi.fn() },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    updateProfile: vi.fn(),
  },
}))
const user: User = {
  id: 'one',
  username: 'one',
  email: 'one@example.test',
  avatar: null,
  createdAt: '2026-10-13T12:00:00Z',
  isActive: true,
  isAdmin: false,
  preferences: { theme: 'hermes', mode: 'light' },
}
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((done, fail) => {
    resolve = done
    reject = fail
  })
  return { promise, resolve, reject }
}
function setup<T>(hook: () => T) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
  return { ...renderHook(hook, { wrapper }), client }
}
beforeEach(() => {
  vi.resetAllMocks()
  localStorage.clear()
  TokenStorage.setTokens({ accessToken: 'access', refreshToken: 'refresh' })
  vi.mocked(authService.getCurrentUser).mockResolvedValue(user)
  vi.mocked(authService.logout).mockImplementation(async () => {
    TokenStorage.clearTokens()
  })
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('session state', () => {
  it('removes inactive caches and cancels in-flight queries before external validation finishes', async () => {
    const { result, client } = setup(useAuth)
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
    const key = ['settings', 'api-keys', 'one'] as const
    client.setQueryData(key, [{ name: 'private A metadata' }])
    client.setQueryData(['admin', 'users'], [{ email: 'private A admin data' }])
    const pending = deferred<string>()
    let signal: AbortSignal | undefined
    const request = client.fetchQuery({
      queryKey: ['account', 'pending'],
      queryFn: (context) => {
        signal = context.signal
        return pending.promise
      },
    }).catch(() => {})
    const validation = deferred<User>()
    vi.mocked(authService.getCurrentUser).mockReturnValue(validation.promise)
    act(() => {
      localStorage.setItem('hermes_access_token', 'B-access')
      localStorage.setItem('hermes_refresh_token', 'B-refresh')
      window.dispatchEvent(new StorageEvent('storage', { key: 'hermes_access_token' }))
    })
    expect(client.getQueryData(key)).toBeUndefined()
    expect(client.getQueryData(['admin', 'users'])).toBeUndefined()
    expect(signal?.aborted).toBe(true)
    expect(result.current.user).toBeNull()
    await act(async () => {
      pending.resolve('late A response')
      await request
      validation.resolve({ ...user, id: 'two' })
    })
    await waitFor(() => expect(result.current.user?.id).toBe('two'))
    expect(client.getQueryData(['account', 'pending'])).toBeUndefined()
    expect(client.getQueryData(key)).toBeUndefined()
  })

  it('scopes API keys to the validated account and discards its late response on a tab switch', async () => {
    const pending = deferred<Awaited<ReturnType<typeof apiClient.getApiKeys>>>()
    vi.mocked(apiClient.getApiKeys).mockReturnValueOnce(pending.promise).mockResolvedValueOnce([])
    const { result, client } = setup(() => ({ auth: useAuth(), keys: useApiKeys() }))
    await waitFor(() => expect(apiClient.getApiKeys).toHaveBeenCalledOnce())
    const signal = vi.mocked(apiClient.getApiKeys).mock.calls[0]?.[0]
    vi.mocked(authService.getCurrentUser).mockResolvedValue({ ...user, id: 'two' })
    act(() => {
      localStorage.setItem('hermes_access_token', 'B-access')
      window.dispatchEvent(new StorageEvent('storage', { key: 'hermes_access_token' }))
    })
    expect(signal?.aborted).toBe(true)
    await waitFor(() => expect(result.current.auth.user?.id).toBe('two'))
    await waitFor(() => expect(result.current.keys.keys.data).toEqual([]))
    await act(async () => pending.resolve([]))
    expect(client.getQueryData(['settings', 'api-keys', 'one'])).toBeUndefined()
    expect(client.getQueryData(['settings', 'api-keys', 'two'])).toEqual([])
    expect(apiClient.getApiKeys).toHaveBeenCalledTimes(2)
  })

  it('removes previous-account data on external logout (storage clear)', async () => {
    const { result, client } = setup(useAuth)
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
    client.setQueryData(['settings', 'api-keys', 'one'], ['private A metadata'])
    act(() => {
      localStorage.clear()
      window.dispatchEvent(new StorageEvent('storage', { key: null }))
    })
    expect(result.current.isAuthenticated).toBe(false)
    expect(client.getQueryCache().getAll()).toHaveLength(1)
    expect(client.getQueryData(['settings', 'api-keys', 'one'])).toBeUndefined()
  })

  it('keeps credentials and offers recovery after boot validation loses the network', async () => {
    vi.mocked(authService.getCurrentUser).mockRejectedValue(new TypeError('Network unavailable'))
    const { result } = setup(useAuth)
    await waitFor(() => expect(result.current.validationError?.message).toBe('Network unavailable'))
    expect(TokenStorage.getAccessToken()).toBe('access')
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
    vi.mocked(authService.getCurrentUser).mockResolvedValue(user)
    act(() => result.current.retryValidation())
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
  })

  it('clears rejected credentials when the server confirms authentication failure', async () => {
    vi.mocked(authService.getCurrentUser).mockRejectedValue(new ApiError(401, 'Session revoked'))
    const { result } = setup(useAuth)
    await waitFor(() => expect(TokenStorage.getRefreshToken()).toBeNull())
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('cannot restore the cached user when boot validation finishes after logout', async () => {
    const validation = deferred<User>()
    vi.mocked(authService.getCurrentUser).mockReturnValue(validation.promise)
    const { result } = setup(useAuth)
    await act(async () => {
      await result.current.logout()
    })
    await act(async () => validation.resolve(user))
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('serializes preference patches against confirmed data after an earlier patch fails', async () => {
    const first = deferred<User>()
    vi.mocked(authService.updateProfile)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ ...user, preferences: { theme: 'hermes', mode: 'dark' } })
    const { result } = setup(useAuth)
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
    let failed!: Promise<void>
    let second!: Promise<void>
    await act(async () => {
      failed = result.current.updatePreferences({ theme: 'nord' }).catch(() => {})
      second = result.current.updatePreferences({ mode: 'dark' })
    })
    first.reject(new Error('Save failed'))
    await act(async () => {
      await Promise.all([failed, second])
    })
    expect(authService.updateProfile).toHaveBeenNthCalledWith(2, {
      preferences: { theme: 'hermes', mode: 'dark' },
    })
    await waitFor(() =>
      expect(result.current.user?.preferences).toEqual({ theme: 'hermes', mode: 'dark' })
    )
  })
  it('keeps a new session established in another tab while logout finishes', async () => {
    const logout = deferred<void>()
    vi.mocked(authService.logout).mockReturnValue(logout.promise)
    const { result } = setup(useAuth)
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
    let pending!: Promise<void>
    await act(async () => {
      pending = result.current.logout()
    })
    vi.mocked(authService.getCurrentUser).mockResolvedValue({ ...user, id: 'two', username: 'two' })
    act(() => TokenStorage.setTokens({ accessToken: 'new-access', refreshToken: 'new-refresh' }))
    await waitFor(() => expect(result.current.user?.id).toBe('two'))
    await act(async () => {
      logout.resolve()
      await pending
    })
    expect(result.current.user?.id).toBe('two')
    expect(TokenStorage.getRefreshToken()).toBe('new-refresh')
  })
})

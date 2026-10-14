import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from '@/services/auth'
import { ApiError } from '@/lib/errors'
import { TokenStorage } from '@/utils/tokenStorage'
import type { User } from '@/types/auth'
import { AuthProvider, useAuth } from './AuthContext'

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
function setup() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
  return { ...renderHook(useAuth, { wrapper }), client }
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
  it('keeps credentials and offers recovery after boot validation loses the network', async () => {
    vi.mocked(authService.getCurrentUser).mockRejectedValue(new TypeError('Network unavailable'))
    const { result } = setup()
    await waitFor(() => expect(result.current.validationError?.message).toBe('Network unavailable'))
    expect(TokenStorage.getAccessToken()).toBe('access')
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
    vi.mocked(authService.getCurrentUser).mockResolvedValue(user)
    act(() => result.current.retryValidation())
    await waitFor(() => expect(result.current.user?.id).toBe('one'))
  })

  it('clears rejected credentials when the server confirms authentication failure', async () => {
    vi.mocked(authService.getCurrentUser).mockRejectedValue(new ApiError(401, 'Session revoked'))
    const { result } = setup()
    await waitFor(() => expect(TokenStorage.getRefreshToken()).toBeNull())
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('cannot restore the cached user when boot validation finishes after logout', async () => {
    const validation = deferred<User>()
    vi.mocked(authService.getCurrentUser).mockReturnValue(validation.promise)
    const { result } = setup()
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
    const { result } = setup()
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
    const { result } = setup()
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

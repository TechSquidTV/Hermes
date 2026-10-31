import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TokenStorage } from '../tokenStorage'

function jwt(exp: number): string {
  return `header.${btoa(JSON.stringify({ exp }))}.signature`
}

describe('TokenStorage', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-13T12:00:00Z'))
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('uses one persistent store and ignores stale tab-local credentials', () => {
    sessionStorage.setItem('hermes_access_token', 'stale')
    TokenStorage.setTokens({ accessToken: 'current', refreshToken: 'refresh' })
    expect(localStorage.getItem('hermes_access_token')).toBe('current')
    expect(TokenStorage.getAccessToken()).toBe('current')
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
    expect(TokenStorage.hasValidTokens()).toBe(true)
  })

  it.each([60, 900, 86_400])(
    'honors the JWT expiry configured by the server (%i seconds)',
    (seconds) => {
      const expires = Date.now() / 1000 + seconds
      const token = jwt(expires)
      TokenStorage.setAccessToken(token)
      expect(TokenStorage.getTokenExpiry()).toBe(expires * 1000)
      expect(TokenStorage.getAccessToken()).toBe(token)
      vi.advanceTimersByTime(seconds * 1000)
      expect(TokenStorage.getAccessToken()).toBeNull()
    }
  )

  it('retains the refresh credential when access expires', () => {
    TokenStorage.setTokens({ accessToken: jwt(Date.now() / 1000), refreshToken: 'refresh' })
    expect(TokenStorage.getAccessToken()).toBeNull()
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
  })

  it.each(['opaque-token', 'header.invalid.signature', 'header.bnVsbA.signature'])(
    'leaves malformed bearer credentials to server validation: %s',
    (token) => {
      TokenStorage.setAccessToken(token)
      expect(TokenStorage.getTokenExpiry()).toBeNull()
      expect(TokenStorage.getAccessToken()).toBe(token)
      expect(TokenStorage.isTokenNearExpiry()).toBe(false)
    }
  )

  it.each([
    [-60, true],
    [240, true],
    [300, true],
    [360, false],
  ] as const)('detects expiry within five minutes (%i seconds)', (seconds, expected) => {
    TokenStorage.setAccessToken(jwt(Date.now() / 1000 + seconds))
    expect(TokenStorage.isTokenNearExpiry()).toBe(expected)
  })

  it('clears access independently and all credentials on logout', () => {
    TokenStorage.setTokens({ accessToken: 'access', refreshToken: 'refresh' })
    TokenStorage.clearAccessToken()
    expect(TokenStorage.getRefreshToken()).toBe('refresh')
    TokenStorage.clearTokens()
    expect(TokenStorage.getAccessToken()).toBeNull()
    expect(TokenStorage.getRefreshToken()).toBeNull()
  })

  it('notifies subscribers for a new login and logout, preserving identity during rotation', () => {
    const listener = vi.fn()
    const unsubscribe = TokenStorage.subscribe(listener)
    const before = TokenStorage.getVersion()
    TokenStorage.setTokens({ accessToken: 'one', refreshToken: 'one' })
    expect(TokenStorage.getVersion()).toBe(before + 1)
    const sessionMarker = localStorage.getItem('hermes_session_change')
    expect(sessionMarker).not.toBeNull()
    TokenStorage.setTokens({ accessToken: 'two', refreshToken: 'two' }, false)
    expect(TokenStorage.getVersion()).toBe(before + 1)
    expect(localStorage.getItem('hermes_session_change')).toBe(sessionMarker)
    TokenStorage.clearTokens()
    expect(localStorage.getItem('hermes_session_change')).not.toBe(sessionMarker)
    expect(listener).toHaveBeenCalledTimes(2)
    unsubscribe()
  })

  it('notifies when another tab changes the session', () => {
    const listener = vi.fn()
    const unsubscribe = TokenStorage.subscribe(listener)
    window.dispatchEvent(new StorageEvent('storage', { key: 'hermes_session_change' }))
    expect(listener).toHaveBeenCalledOnce()
    unsubscribe()
  })

  it('handles unavailable persistent storage', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Denied')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Denied')
    })
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('Denied')
    })
    expect(() =>
      TokenStorage.setTokens({ accessToken: 'access', refreshToken: 'refresh' })
    ).not.toThrow()
    expect(TokenStorage.hasValidTokens()).toBe(false)
    expect(() => TokenStorage.clearTokens()).not.toThrow()
  })
})

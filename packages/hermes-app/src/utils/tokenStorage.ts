import { debug } from '@/lib/debug'
import type { components } from '@/types/api.generated'

type Tokens = Pick<components['schemas']['TokenResponse'], 'accessToken' | 'refreshToken'>

/** Credentials persist in localStorage. They are accessible to same-origin scripts. */
export class TokenStorage {
  private static readonly ACCESS_TOKEN_KEY = 'hermes_access_token'
  private static readonly REFRESH_TOKEN_KEY = 'hermes_refresh_token'
  private static readonly SESSION_KEY = 'hermes_session_change'
  private static version = 0

  private static listeners = new Set<() => void>()
  static getVersion = (): number => TokenStorage.version
  private static notify(): void {
    this.listeners.forEach((listener) => listener())
  }
  private static onStorage = (event: StorageEvent): void => {
    if (
      event.key === null ||
      event.key === TokenStorage.SESSION_KEY
    ) {
      TokenStorage.version += 1
      TokenStorage.notify()
    }
  }
  static subscribe = (listener: () => void): (() => void) => {
    if (TokenStorage.listeners.size === 0)
      window.addEventListener('storage', TokenStorage.onStorage)
    TokenStorage.listeners.add(listener)
    return () => {
      TokenStorage.listeners.delete(listener)
      if (TokenStorage.listeners.size === 0)
        window.removeEventListener('storage', TokenStorage.onStorage)
    }
  }

  static setTokens(tokens: Tokens, newSession = true): void {
    if (newSession) this.version += 1
    this.setAccessToken(tokens.accessToken)
    this.setRefreshToken(tokens.refreshToken)
    if (newSession) this.publishSessionChange()
  }

  private static publishSessionChange(): void {
    try {
      // This is a notification marker, not a credential or a security token.
      localStorage.setItem(this.SESSION_KEY, `${Date.now()}-${Math.random()}`)
    } catch (error) {
      debug.error('Unable to publish session change', error)
    }
    this.notify()
  }

  static setAccessToken(token: string): void {
    try {
      localStorage.setItem(this.ACCESS_TOKEN_KEY, token)
    } catch (error) {
      debug.error('Unable to store access token', error)
    }
  }

  static getTokenExpiry(): number | null {
    const token = this.read(this.ACCESS_TOKEN_KEY)
    const encoded = token?.split('.')[1]
    if (!encoded) return null
    try {
      const payload: { exp?: number } = JSON.parse(
        atob(encoded.replace(/-/g, '+').replace(/_/g, '/'))
      )
      return typeof payload.exp === 'number' && Number.isFinite(payload.exp)
        ? payload.exp * 1000
        : null
    } catch {
      return null
    }
  }

  static getAccessToken(): string | null {
    const expiry = this.getTokenExpiry()
    if (expiry !== null && Date.now() >= expiry) return null
    return this.read(this.ACCESS_TOKEN_KEY)
  }

  static setRefreshToken(token: string): void {
    try {
      localStorage.setItem(this.REFRESH_TOKEN_KEY, token)
    } catch (error) {
      debug.error('Unable to store refresh token', error)
    }
  }

  private static read(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  }

  static getRefreshToken(): string | null {
    return this.read(this.REFRESH_TOKEN_KEY)
  }

  static clearTokens(): void {
    this.version += 1
    this.clearAccessToken()
    try {
      localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    } catch (error) {
      debug.error('Unable to clear refresh token', error)
    }
    this.publishSessionChange()
  }

  static clearAccessToken(): void {
    try {
      localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    } catch (error) {
      debug.error('Unable to clear access token', error)
    }
  }

  static hasValidTokens(): boolean {
    return !!(this.getAccessToken() && this.getRefreshToken())
  }

  static isTokenNearExpiry(): boolean {
    const expiry = this.getTokenExpiry()
    return expiry !== null && expiry <= Date.now() + 5 * 60_000
  }
}

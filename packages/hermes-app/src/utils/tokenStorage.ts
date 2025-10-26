// Secure token storage utilities

export class TokenStorage {
  private static readonly ACCESS_TOKEN_KEY = 'hermes_access_token'
  private static readonly REFRESH_TOKEN_KEY = 'hermes_refresh_token'
  private static readonly TOKEN_EXPIRY_KEY = 'hermes_token_expiry'

  /**
   * Store access token with optional expiry
   */
  static setAccessToken(token: string, expiresInMinutes?: number): void {
    try {
      // Store in sessionStorage for additional security
      sessionStorage.setItem(this.ACCESS_TOKEN_KEY, token)

      // Also store in localStorage for persistence across browser sessions
      localStorage.setItem(this.ACCESS_TOKEN_KEY, token)

      // Store expiry time if provided
      if (expiresInMinutes) {
        const expiryTime = Date.now() + (expiresInMinutes * 60 * 1000)
        localStorage.setItem(this.TOKEN_EXPIRY_KEY, expiryTime.toString())
      }

      console.log('[TokenStorage] Access token stored securely')
    } catch (error) {
      console.warn('[TokenStorage] SessionStorage failed, falling back to localStorage:', error)
      localStorage.setItem(this.ACCESS_TOKEN_KEY, token)
    }
  }

  /**
   * Get access token, checking expiry
   */
  static getAccessToken(): string | null {
    try {
      // Try sessionStorage first
      const token = sessionStorage.getItem(this.ACCESS_TOKEN_KEY) ||
                   localStorage.getItem(this.ACCESS_TOKEN_KEY)

      console.log('[TokenStorage] getAccessToken - token found:', !!token, 'source:', token ? (sessionStorage.getItem(this.ACCESS_TOKEN_KEY) ? 'sessionStorage' : 'localStorage') : 'none')

      if (!token) {
        console.log('[TokenStorage] getAccessToken - no token found')
        return null
      }

      // Check if token has expired
      const expiryTime = localStorage.getItem(this.TOKEN_EXPIRY_KEY)
      if (expiryTime) {
        const isExpired = Date.now() > parseInt(expiryTime)
        console.log('[TokenStorage] getAccessToken - expiry check:', { expiryTime: new Date(parseInt(expiryTime)), isExpired })
        if (isExpired) {
          this.clearTokens()
          console.log('[TokenStorage] Token expired, cleared automatically')
          return null
        }
      }

      console.log('[TokenStorage] getAccessToken - returning valid token, length:', token.length, 'preview:', token.substring(0, 20) + '...')
      return token
    } catch (error) {
      console.warn('[TokenStorage] Error retrieving token:', error)
      return localStorage.getItem(this.ACCESS_TOKEN_KEY)
    }
  }

  /**
   * Store refresh token (longer term storage)
   */
  static setRefreshToken(token: string): void {
    try {
      // Use localStorage for refresh tokens (longer persistence)
      localStorage.setItem(this.REFRESH_TOKEN_KEY, token)
      console.log('[TokenStorage] Refresh token stored')
    } catch (error) {
      console.warn('[TokenStorage] Failed to store refresh token:', error)
    }
  }

  /**
   * Get refresh token
   */
  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }

  /**
   * Clear all tokens
   */
  static clearTokens(): void {
    try {
      sessionStorage.removeItem(this.ACCESS_TOKEN_KEY)
    } catch (error) {
      console.warn('[TokenStorage] Failed to clear sessionStorage:', error)
    }

    localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    localStorage.removeItem(this.TOKEN_EXPIRY_KEY)

    console.log('[TokenStorage] All tokens cleared')
  }

  /**
   * Check if user has valid tokens
   */
  static hasValidTokens(): boolean {
    const token = this.getAccessToken()
    const refreshToken = this.getRefreshToken()
    return !!(token && refreshToken)
  }

  /**
   * Get token expiry time
   */
  static getTokenExpiry(): number | null {
    const expiryTime = localStorage.getItem(this.TOKEN_EXPIRY_KEY)
    return expiryTime ? parseInt(expiryTime) : null
  }

  /**
   * Check if token is close to expiry (within 5 minutes)
   */
  static isTokenNearExpiry(): boolean {
    const expiryTime = this.getTokenExpiry()
    if (!expiryTime) return false

    const fiveMinutesFromNow = Date.now() + (5 * 60 * 1000)
    return expiryTime <= fiveMinutesFromNow
  }
}

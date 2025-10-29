/**
 * Tests for TokenStorage utility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { TokenStorage } from '../tokenStorage'

// Mock localStorage and sessionStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

// Setup mocks
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock
})

describe('TokenStorage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
    sessionStorageMock.getItem.mockReturnValue(null)
  })

  describe('setAccessToken', () => {
    it('should store token in both storages', () => {
      const token = 'test-access-token'
      const expiryMinutes = 15

      TokenStorage.setAccessToken(token, expiryMinutes)

      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_access_token',
        token
      )
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_access_token',
        token
      )
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_token_expiry',
        expect.any(String)
      )
    })

    it('should handle sessionStorage errors gracefully', () => {
      sessionStorageMock.setItem.mockImplementation(() => {
        throw new Error('SessionStorage full')
      })

      const token = 'test-access-token'

      // Should not throw error
      expect(() => {
        TokenStorage.setAccessToken(token)
      }).not.toThrow()

      // Should still store in localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_access_token',
        token
      )
    })

    it('should handle both localStorage and sessionStorage errors gracefully', () => {
      sessionStorageMock.setItem.mockImplementation(() => {
        throw new Error('SessionStorage full')
      })
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('LocalStorage full')
      })

      const token = 'test-access-token'

      // Should not throw error even when both storages fail
      expect(() => {
        TokenStorage.setAccessToken(token)
      }).not.toThrow()
    })

    it('should store token without expiry when expiresInMinutes not provided', () => {
      const token = 'test-access-token'

      TokenStorage.setAccessToken(token)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_access_token',
        token
      )
      // Should not set expiry
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        'hermes_token_expiry',
        expect.any(String)
      )
    })
  })

  describe('getAccessToken', () => {
    it('should return token from sessionStorage first', () => {
      const token = 'test-token'
      sessionStorageMock.getItem.mockReturnValue(token)

      const result = TokenStorage.getAccessToken()

      expect(sessionStorageMock.getItem).toHaveBeenCalledWith('hermes_access_token')
      expect(result).toBe(token)
    })

    it('should fall back to localStorage if sessionStorage empty', () => {
      const token = 'test-token'
      sessionStorageMock.getItem.mockReturnValue(null)
      localStorageMock.getItem.mockReturnValue(token)

      const result = TokenStorage.getAccessToken()

      expect(localStorageMock.getItem).toHaveBeenCalledWith('hermes_access_token')
      expect(result).toBe(token)
    })

    it('should return null if no token found', () => {
      sessionStorageMock.getItem.mockReturnValue(null)
      localStorageMock.getItem.mockReturnValue(null)

      const result = TokenStorage.getAccessToken()

      expect(result).toBeNull()
    })

    it('should clear expired tokens', () => {
      const expiredTime = Date.now() - 1000 // 1 second ago
      localStorageMock.getItem
        .mockReturnValueOnce('test-token') // token
        .mockReturnValueOnce(expiredTime.toString()) // expiry

      const result = TokenStorage.getAccessToken()

      expect(result).toBeNull()
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_refresh_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_token_expiry')
    })

    it('should handle storage errors and fall back gracefully', () => {
      sessionStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage error')
      })
      localStorageMock.getItem.mockReturnValue('fallback-token')

      const result = TokenStorage.getAccessToken()

      expect(result).toBe('fallback-token')
    })

    it('should return null when both storages throw errors', () => {
      sessionStorageMock.getItem.mockImplementation(() => {
        throw new Error('SessionStorage error')
      })
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('LocalStorage error')
      })

      const result = TokenStorage.getAccessToken()

      expect(result).toBeNull()
    })

    it('should handle invalid expiry time gracefully', () => {
      localStorageMock.getItem
        .mockReturnValueOnce('test-token')
        .mockReturnValueOnce('invalid-expiry-time')

      // Should not throw, parseInt will return NaN
      const result = TokenStorage.getAccessToken()

      // Should return token when expiry is invalid (NaN)
      expect(result).toBe('test-token')
    })

    it('should return token when expiry is exactly now', () => {
      const nowTime = Date.now()
      localStorageMock.getItem
        .mockReturnValueOnce('test-token')
        .mockReturnValueOnce(nowTime.toString())

      const result = TokenStorage.getAccessToken()

      // Token is NOT expired when Date.now() === expiry time (requires Date.now() > expiry to be expired)
      expect(result).toBe('test-token')
    })
  })

  describe('setRefreshToken', () => {
    it('should store refresh token in localStorage', () => {
      const token = 'test-refresh-token'

      TokenStorage.setRefreshToken(token)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'hermes_refresh_token',
        token
      )
    })

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('LocalStorage full')
      })

      const token = 'test-refresh-token'

      // Should not throw error
      expect(() => {
        TokenStorage.setRefreshToken(token)
      }).not.toThrow()
    })
  })

  describe('getRefreshToken', () => {
    it('should return refresh token from localStorage', () => {
      const token = 'test-refresh-token'
      localStorageMock.getItem.mockReturnValue(token)

      const result = TokenStorage.getRefreshToken()

      expect(localStorageMock.getItem).toHaveBeenCalledWith('hermes_refresh_token')
      expect(result).toBe(token)
    })

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('LocalStorage error')
      })

      const result = TokenStorage.getRefreshToken()

      expect(result).toBeNull()
    })
  })

  describe('clearTokens', () => {
    it('should clear all tokens from both storages', () => {
      TokenStorage.clearTokens()

      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('hermes_access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_refresh_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_token_expiry')
    })

    it('should handle sessionStorage errors gracefully', () => {
      sessionStorageMock.removeItem.mockImplementation(() => {
        throw new Error('SessionStorage error')
      })

      // Should not throw error
      expect(() => {
        TokenStorage.clearTokens()
      }).not.toThrow()

      // Should still clear localStorage
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_refresh_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('hermes_token_expiry')
    })

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.removeItem.mockImplementation(() => {
        throw new Error('LocalStorage error')
      })

      // Should not throw error
      expect(() => {
        TokenStorage.clearTokens()
      }).not.toThrow()
    })
  })

  describe('hasValidTokens', () => {
    it('should return true when both tokens exist', () => {
      localStorageMock.getItem
        .mockReturnValueOnce('access-token')  // access token
        .mockReturnValueOnce(null)  // expiry (no expiry set)
        .mockReturnValueOnce('refresh-token') // refresh token

      const result = TokenStorage.hasValidTokens()

      expect(result).toBe(true)
    })

    it('should return false when tokens are missing', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const result = TokenStorage.hasValidTokens()

      expect(result).toBe(false)
    })
  })

  describe('getTokenExpiry', () => {
    it('should return expiry time when set', () => {
      const expiryTime = Date.now() + (15 * 60 * 1000)
      localStorageMock.getItem.mockReturnValue(expiryTime.toString())

      const result = TokenStorage.getTokenExpiry()

      expect(result).toBe(expiryTime)
    })

    it('should return null when no expiry set', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const result = TokenStorage.getTokenExpiry()

      expect(result).toBeNull()
    })

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('LocalStorage error')
      })

      const result = TokenStorage.getTokenExpiry()

      expect(result).toBeNull()
    })

    it('should handle invalid expiry string', () => {
      localStorageMock.getItem.mockReturnValue('not-a-number')

      const result = TokenStorage.getTokenExpiry()

      // parseInt('not-a-number') returns NaN
      expect(isNaN(result as number)).toBe(true)
    })
  })

  describe('isTokenNearExpiry', () => {
    it('should return true when token expires within 5 minutes', () => {
      const fourMinutesFromNow = Date.now() + (4 * 60 * 1000)
      localStorageMock.getItem.mockReturnValue(fourMinutesFromNow.toString())

      const result = TokenStorage.isTokenNearExpiry()

      expect(result).toBe(true)
    })

    it('should return false when token expires later', () => {
      const sixMinutesFromNow = Date.now() + (6 * 60 * 1000)
      localStorageMock.getItem.mockReturnValue(sixMinutesFromNow.toString())

      const result = TokenStorage.isTokenNearExpiry()

      expect(result).toBe(false)
    })

    it('should return false when no expiry set', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const result = TokenStorage.isTokenNearExpiry()

      expect(result).toBe(false)
    })

    it('should return true when token expires exactly in 5 minutes', () => {
      const fiveMinutesFromNow = Date.now() + (5 * 60 * 1000)
      localStorageMock.getItem.mockReturnValue(fiveMinutesFromNow.toString())

      const result = TokenStorage.isTokenNearExpiry()

      expect(result).toBe(true)
    })

    it('should return true when token is already expired', () => {
      const oneMinuteAgo = Date.now() - (1 * 60 * 1000)
      localStorageMock.getItem.mockReturnValue(oneMinuteAgo.toString())

      const result = TokenStorage.isTokenNearExpiry()

      expect(result).toBe(true)
    })
  })
})

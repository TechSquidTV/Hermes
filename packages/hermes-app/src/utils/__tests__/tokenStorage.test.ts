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
  })

  describe('getRefreshToken', () => {
    it('should return refresh token from localStorage', () => {
      const token = 'test-refresh-token'
      localStorageMock.getItem.mockReturnValue(token)

      const result = TokenStorage.getRefreshToken()

      expect(localStorageMock.getItem).toHaveBeenCalledWith('hermes_refresh_token')
      expect(result).toBe(token)
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
  })
})

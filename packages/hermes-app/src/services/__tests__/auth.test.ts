/**
 * Tests for AuthService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authService } from '../auth'
import { TokenStorage } from '@/utils/tokenStorage'

// Mock fetch
global.fetch = vi.fn()

// Mock TokenStorage
vi.mock('@/utils/tokenStorage')

const mockFetch = fetch as any
const mockTokenStorage = TokenStorage as any

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTokenStorage.getAccessToken.mockReturnValue(null)
    mockTokenStorage.getRefreshToken.mockReturnValue(null)
    // Reset fetch mock for localStorage access in authService
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)
  })

  describe('login', () => {
    it('should successfully login and store tokens', async () => {
      const mockResponse = {
        accessToken: 'access-token-123',
        refreshToken: 'refresh-token-456',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          createdAt: new Date().toISOString()
        }
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      } as Response)

      mockTokenStorage.setAccessToken.mockImplementation(() => {})
      mockTokenStorage.setRefreshToken.mockImplementation(() => {})

      const result = await authService.login({
        username: 'testuser',
        password: 'password123'
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/login',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({
            username: 'testuser',
            password: 'password123'
          })
        })
      )

      expect(mockTokenStorage.setAccessToken).toHaveBeenCalledWith('access-token-123', 15)
      expect(mockTokenStorage.setRefreshToken).toHaveBeenCalledWith('refresh-token-456')
      expect(result).toEqual(mockResponse)
    })

    it('should handle login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' })
      } as Response)

      await expect(authService.login({
        username: 'testuser',
        password: 'wrongpassword'
      })).rejects.toThrow('401')

      expect(mockTokenStorage.setAccessToken).not.toHaveBeenCalled()
      expect(mockTokenStorage.setRefreshToken).not.toHaveBeenCalled()
    })
  })

  describe('getCurrentUser', () => {
    it('should get current user with valid token', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        createdAt: new Date().toISOString()
      }

      mockTokenStorage.getAccessToken.mockReturnValue('valid-token')
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser
      } as Response)

      const result = await authService.getCurrentUser()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/me',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer valid-token'
          })
        })
      )

      expect(result).toEqual(mockUser)
    })

    it('should handle unauthorized error', async () => {
      mockTokenStorage.getAccessToken.mockReturnValue('invalid-token')
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token expired' })
      } as Response)

      await expect(authService.getCurrentUser()).rejects.toThrow('401')
    })
  })

  describe('refreshToken', () => {
    it('should refresh token successfully', async () => {
      const mockResponse = {
        accessToken: 'new-access-token',
        refreshToken: 'new-refresh-token',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          createdAt: new Date().toISOString()
        }
      }

      mockTokenStorage.getRefreshToken.mockReturnValue('valid-refresh-token')
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      } as Response)

      mockTokenStorage.setAccessToken.mockImplementation(() => {})
      mockTokenStorage.setRefreshToken.mockImplementation(() => {})

      const result = await authService.refreshToken()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ refreshToken: 'valid-refresh-token' })
        })
      )

      expect(mockTokenStorage.setAccessToken).toHaveBeenCalledWith('new-access-token', 15)
      expect(mockTokenStorage.setRefreshToken).toHaveBeenCalledWith('new-refresh-token')
      expect(result).toEqual(mockResponse)
    })

    it('should throw error when no refresh token available', async () => {
      mockTokenStorage.getRefreshToken.mockReturnValue(null)

      await expect(authService.refreshToken()).rejects.toThrow('No refresh token available')

      expect(mockFetch).not.toHaveBeenCalled()
    })
  })

  describe('logout', () => {
    it('should logout and clear tokens', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      } as Response)

      mockTokenStorage.clearTokens.mockImplementation(() => {})

      await authService.logout()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/logout',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      )

      expect(mockTokenStorage.clearTokens).toHaveBeenCalled()
    })

    it('should clear tokens even if API call fails', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server error' })
      } as Response)

      mockTokenStorage.clearTokens.mockImplementation(() => {})

      await authService.logout()

      expect(mockTokenStorage.clearTokens).toHaveBeenCalled()
    })
  })

  describe('private request method', () => {
    it('should include auth token in headers when available', async () => {
      mockTokenStorage.getAccessToken.mockReturnValue('test-token')
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      } as Response)

      await authService.getCurrentUser()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/me',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          })
        })
      )
    })

    it('should handle 401 errors with detailed messages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token expired' })
      } as Response)

      await expect(authService.getCurrentUser()).rejects.toThrow('401')
    })
  })
})

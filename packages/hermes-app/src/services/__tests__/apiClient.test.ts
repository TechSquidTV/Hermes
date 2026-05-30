/**
 * Tests for API client API key methods
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { apiClient } from '../api/client'
import { TokenStorage } from '@/utils/tokenStorage'

// Mock fetch
global.fetch = vi.fn()

const mockFetch = fetch as any

describe('ApiClient - API Key Methods', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('createApiKey', () => {
    it('should create API key successfully', async () => {
      const mockResponse = {
        id: '1',
        name: 'Test Key',
        key: 'hm_1234567890abcdef',
        permissions: ['read', 'write'],
        rate_limit: 60,
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
        last_used: null,
        expires_at: null,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await apiClient.createApiKey({
        name: 'Test Key',
        permissions: ['read', 'write'],
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/api-keys',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            name: 'Test Key',
            permissions: ['read', 'write'],
          }),
        })
      )

      expect(result).toEqual(mockResponse)
    })

    it('should handle create API key error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Validation error' }),
      } as Response)

      await expect(
        apiClient.createApiKey({
          name: '',
          permissions: [],
        })
      ).rejects.toThrow('Authentication error')
    })
  })

  describe('getApiKeys', () => {
    it('should fetch API keys successfully', async () => {
      const mockApiKeys = [
        {
          id: '1',
          name: 'Test Key 1',
          permissions: ['read'],
          rate_limit: 60,
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
          last_used: '2025-01-02T00:00:00Z',
          expires_at: null,
        },
        {
          id: '2',
          name: 'Test Key 2',
          permissions: ['write'],
          rate_limit: 30,
          is_active: false,
          created_at: '2025-01-01T00:00:00Z',
          last_used: null,
          expires_at: null,
        },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockApiKeys,
      } as Response)

      const result = await apiClient.getApiKeys()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/api-keys',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )

      expect(result).toEqual(mockApiKeys)
    })

    it('should handle get API keys error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Unauthorized' }),
      } as Response)

      await expect(apiClient.getApiKeys()).rejects.toThrow('403: Access denied')
    })

    it('should retry 401 responses with the refreshed access token', async () => {
      const mockApiKeys = [
        {
          id: '1',
          name: 'Test Key',
          permissions: ['read'],
          rate_limit: 60,
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
          last_used: null,
          expires_at: null,
        },
      ]

      const getAccessTokenSpy = vi
        .spyOn(TokenStorage, 'getAccessToken')
        .mockReturnValueOnce('expired-token')
        .mockReturnValueOnce('fresh-token')
      vi.spyOn(TokenStorage, 'getRefreshToken').mockReturnValue('refresh-token')
      const setAccessTokenSpy = vi.spyOn(TokenStorage, 'setAccessToken').mockImplementation(() => {})
      const setRefreshTokenSpy = vi.spyOn(TokenStorage, 'setRefreshToken').mockImplementation(() => {})

      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            accessToken: 'fresh-token',
            refreshToken: 'fresh-refresh-token',
            tokenType: 'bearer',
          }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiKeys,
        } as Response)

      const result = await apiClient.request<typeof mockApiKeys>('/auth/api-keys', {
        headers: {
          Authorization: 'Bearer expired-token',
        },
      })

      expect(result).toEqual(mockApiKeys)
      expect(setAccessTokenSpy).toHaveBeenCalledWith('fresh-token', 15)
      expect(setRefreshTokenSpy).toHaveBeenCalledWith('fresh-refresh-token')
      expect(getAccessTokenSpy).toHaveBeenCalledTimes(2)
      expect(mockFetch).toHaveBeenNthCalledWith(
        3,
        '/api/v1/auth/api-keys',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer fresh-token',
          }),
        })
      )
    })
  })

  describe('revokeApiKey', () => {
    it('should revoke API key successfully', async () => {
      const mockResponse = {
        message: 'API key revoked successfully!',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await apiClient.revokeApiKey('test-key-id')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/api-keys/test-key-id',
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )

      expect(result).toEqual(mockResponse)
    })

    it('should handle revoke API key error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'API key not found' }),
      } as Response)

      await expect(apiClient.revokeApiKey('nonexistent-id')).rejects.toThrow(
        'Authentication error'
      )
    })
  })

  describe('query parameter methods', () => {
    it('serializes defined file filters and skips undefined values', async () => {
      const mockResponse = {
        files: [],
        totalCount: 0,
        totalSize: 0,
        directory: '/downloads',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await apiClient.getDownloadedFiles({
        extension: 'mp4',
        limit: 25,
        offset: 0,
        max_size: undefined,
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/files/?extension=mp4&limit=25&offset=0',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('combines timeline period with optional filters consistently', async () => {
      const mockResponse = [
        {
          date: '2026-01-01',
          downloads: 1,
          successful: 1,
          failed: 0,
          totalSize: 1024,
          avgDuration: 10,
          successRate: 1,
        },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await apiClient.getTimelineStats('month', {
        extractor: 'youtube',
        status: 'completed',
        start_date: undefined,
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/timeline/?period=month&extractor=youtube&status=completed',
        expect.any(Object)
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('health checks', () => {
    it('fetches health without attaching auth state', async () => {
      const getAccessTokenSpy = vi
        .spyOn(TokenStorage, 'getAccessToken')
        .mockReturnValue('stale-token')
      const mockResponse = {
        status: 'healthy',
        version: 'v0.4.2',
        environment: 'production',
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await apiClient.getHealth()

      expect(getAccessTokenSpy).not.toHaveBeenCalled()
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/health/',
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })
})

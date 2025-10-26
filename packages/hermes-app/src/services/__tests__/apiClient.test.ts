/**
 * Tests for API client API key methods
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { apiClient } from '../api/client'

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
})

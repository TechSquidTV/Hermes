/**
 * Tests for useApiKeys hook
 */

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode, createElement } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useApiKeys } from '../useApiKeys'
import { apiClient } from '@/services/api/client'

// Mock the API client
vi.mock('@/services/api/client')

const mockApiClient = apiClient as any

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe.skip('keys query', () => {
    it('should fetch API keys successfully', async () => {
      const mockApiKeys = [
        {
          id: '1',
          name: 'Test Key 1',
          permissions: ['read', 'write'],
          rate_limit: 60,
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
          last_used: '2025-01-02T00:00:00Z',
          expires_at: null,
        },
        {
          id: '2',
          name: 'Test Key 2',
          permissions: ['read'],
          rate_limit: 30,
          is_active: false,
          created_at: '2025-01-01T00:00:00Z',
          last_used: null,
          expires_at: null,
        },
      ]

      mockApiClient.getApiKeys.mockResolvedValue(mockApiKeys)

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      expect(mockApiClient.getApiKeys).toHaveBeenCalledTimes(1)
      expect(result.current.keys.data).toEqual(mockApiKeys)
    })

    it('should handle API key fetch error', async () => {
      mockApiClient.getApiKeys.mockRejectedValue(new Error('API Error'))

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isError).toBe(true)
      })

      expect(result.current.keys.error).toBeDefined()
    })
  })

  describe.skip('createKey mutation', () => {
    it('should create API key successfully', async () => {
      const mockNewKey = {
        id: '3',
        name: 'New Test Key',
        key: 'hm_1234567890abcdef1234567890abcdef',
        permissions: ['read'],
        rate_limit: 60,
        is_active: true,
        created_at: '2025-01-03T00:00:00Z',
        last_used: null,
        expires_at: null,
      }

      mockApiClient.createApiKey.mockResolvedValue(mockNewKey)

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      const createResult = await result.current.createKey.mutateAsync({
        name: 'New Test Key',
        permissions: ['read'],
      })

      expect(mockApiClient.createApiKey).toHaveBeenCalledWith({
        name: 'New Test Key',
        permissions: ['read'],
      })
      expect(createResult).toEqual(mockNewKey)
    })

    it('should handle API key creation error', async () => {
      mockApiClient.createApiKey.mockRejectedValue(new Error('Creation failed'))

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      await expect(
        result.current.createKey.mutateAsync({
          name: 'Test Key',
          permissions: ['read'],
        })
      ).rejects.toThrow('Creation failed')
    })
  })

  describe.skip('revokeKey mutation', () => {
    it('should revoke API key successfully', async () => {
      const mockResponse = { message: 'API key revoked successfully!' }
      mockApiClient.revokeApiKey.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      const revokeResult = await result.current.revokeKey.mutateAsync('test-key-id')

      expect(mockApiClient.revokeApiKey).toHaveBeenCalledWith('test-key-id')
      expect(revokeResult).toEqual(mockResponse)
    })

    it('should handle API key revocation error', async () => {
      mockApiClient.revokeApiKey.mockRejectedValue(new Error('Revocation failed'))

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      await expect(result.current.revokeKey.mutateAsync('test-key-id')).rejects.toThrow(
        'Revocation failed'
      )
    })
  })

  describe.skip('loading states', () => {
    it('should show loading state during operations', async () => {
      mockApiClient.getApiKeys.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 100))
      )

      const { result } = renderHook(() => useApiKeys(), {
        wrapper: createWrapper(),
      })

      // Should be loading initially
      expect(result.current.isLoading).toBe(true)

      await waitFor(() => {
        expect(result.current.keys.isSuccess).toBe(true)
      })

      // Should not be loading after success
      expect(result.current.isLoading).toBe(false)
    })
  })
})

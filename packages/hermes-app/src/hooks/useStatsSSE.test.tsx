/**
 * Tests for useStatsSSE hook
 *
 * This hook manages SSE connections for stats updates and
 * invalidates React Query cache when updates arrive.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useStatsSSE } from './useStatsSSE'
import * as apiClientModule from '@/services/api/client'
import * as useSSEModule from './useSSE'
import type { ReactNode } from 'react'

// Mock dependencies
vi.mock('@/services/api/client')
vi.mock('./useSSE')

describe('useStatsSSE', () => {
  let queryClient: QueryClient
  const mockSSEToken = 'sse_stats_token_xyz789'

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  describe('Token Fetching', () => {
    it('fetches SSE token with stats scope on mount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: 'stats',
          ttl: 600,
        })
      })
    })

    it('only fetches token once on mount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { rerender } = renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledTimes(1)
      })

      // Rerender should not fetch token again
      rerender()
      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledTimes(1)
      })
    })

    it('handles token fetch error gracefully', async () => {
      const mockError = new Error('Token fetch failed')
      const mockCreateSSEToken = vi.fn().mockRejectedValue(mockError)

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to fetch SSE token for stats:',
          mockError
        )
        expect(result.current.error).toEqual(mockError)
      })

      consoleErrorSpy.mockRestore()
    })
  })

  describe('SSE Connection', () => {
    it('fetches token and prepares SSE connection', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const mockUseSSE = vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      // Verify token is fetched with correct parameters
      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: 'stats',
          ttl: 600,
        })
      })

      // Verify useSSE is being called
      expect(mockUseSSE).toHaveBeenCalled()
    })

    it('returns connection state from useSSE', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: { event: 'download_completed', download_id: 'test-123', timestamp: '2025-01-01T00:00:00Z' },
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
        expect(result.current.data).toEqual({
          event: 'download_completed',
          download_id: 'test-123',
          timestamp: '2025-01-01T00:00:00Z',
        })
      })
    })
  })

  describe('Cache Invalidation', () => {
    it('invalidates stats queries when updates arrive', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const statsUpdate = {
        event: 'download_completed' as const,
        download_id: 'test-123',
        timestamp: '2025-01-01T00:00:00Z',
      }

      // Mock useSSE to return data
      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: statsUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const wrapper = createWrapper()
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      renderHook(() => useStatsSSE(), { wrapper })

      await waitFor(() => {
        // Should invalidate queue stats queries
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['queue', 'stats'],
          exact: false,
        })
      })

      // Should also invalidate analytics and timeline queries
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['analytics'],
        exact: false,
      })
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['timeline'],
        exact: false,
      })
    })
  })

  describe('Error Handling', () => {
    it('returns token error if token fetch fails', async () => {
      const tokenError = new Error('Failed to fetch SSE token')
      const mockCreateSSEToken = vi.fn().mockRejectedValue(tokenError)

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(console, 'error').mockImplementation(() => {})

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.error).toEqual(tokenError)
      })
    })

    it('returns SSE error if connection fails', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'stats',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const sseError = new Error('SSE connection failed')

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: false,
        error: sseError,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useStatsSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.error).toEqual(sseError)
      })
    })
  })
})

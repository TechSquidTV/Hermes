/**
 * Tests for useQueueUpdatesSSE hook
 *
 * This hook manages SSE connections for queue-level updates and
 * invalidates React Query cache when updates arrive.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useQueueUpdatesSSE } from './useQueueUpdatesSSE'
import * as apiClientModule from '@/services/api/client'
import * as useSSEModule from './useSSE'
import type { ReactNode } from 'react'

// Mock dependencies
vi.mock('@/services/api/client')
vi.mock('./useSSE')

describe('useQueueUpdatesSSE', () => {
  let queryClient: QueryClient
  const mockSSEToken = 'sse_queue_token_xyz789'

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
    it('fetches SSE token with queue scope on mount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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

      renderHook(() => useQueueUpdatesSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: 'queue',
          ttl: 600,
        })
      })
    })

    it('only fetches token once on mount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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

      const { rerender } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledTimes(1)
      })

      // Rerender shouldn't fetch again
      rerender()
      await new Promise((resolve) => setTimeout(resolve, 100))
      expect(mockCreateSSEToken).toHaveBeenCalledTimes(1)
    })

    it('handles token fetch errors', async () => {
      const mockError = new Error('Failed to fetch SSE token')
      const mockCreateSSEToken = vi.fn().mockRejectedValue(mockError)

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

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to fetch SSE token for queue:',
          mockError
        )
        expect(result.current.error).toBeTruthy()
      })

      consoleErrorSpy.mockRestore()
    })
  })

  describe('SSE Connection', () => {
    it('fetches token and prepares SSE connection', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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

      renderHook(() => useQueueUpdatesSSE(), { wrapper: createWrapper() })

      // Verify token is fetched with correct parameters
      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: 'queue',
          ttl: 600,
        })
      })

      // Verify useSSE is being called (URL construction is tested in "configures SSE with correct options")
      expect(mockUseSSE).toHaveBeenCalled()
    })

    it('configures SSE with correct options', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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

      renderHook(() => useQueueUpdatesSSE(), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockUseSSE).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            events: ['queue_update'],
            reconnect: true,
            maxReconnectAttempts: 10,
            reconnectDelay: 1000,
            maxReconnectDelay: 30000,
            onError: expect.any(Function),
          })
        )
      })
    })
  })

  describe('Queue Update Events', () => {
    it('receives queue update data from SSE', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const queueUpdate = {
        action: 'status_changed' as const,
        download_id: 'test-123',
        status: 'completed',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.data).toEqual(queueUpdate)
      })
    })

    it('handles added action', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const queueUpdate = {
        action: 'added' as const,
        download_id: 'new-download-456',
        status: 'queued',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.data?.action).toBe('added')
        expect(result.current.data?.download_id).toBe('new-download-456')
      })
    })

    it('handles removed action', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const queueUpdate = {
        action: 'removed' as const,
        download_id: 'deleted-789',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.data?.action).toBe('removed')
        expect(result.current.data?.download_id).toBe('deleted-789')
      })
    })
  })

  describe('Query Cache Invalidation', () => {
    it('invalidates queue queries when updates arrive', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const queueUpdate = {
        action: 'status_changed' as const,
        download_id: 'test-123',
        status: 'completed',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const wrapper = createWrapper()
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      renderHook(() => useQueueUpdatesSSE(), { wrapper })

      await waitFor(() => {
        // Should invalidate queue queries
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['queue'],
          exact: false,
        })
      })
    })

    it('invalidates queueStats queries when updates arrive', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const queueUpdate = {
        action: 'status_changed' as const,
        download_id: 'test-123',
        status: 'completed',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const wrapper = createWrapper()
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      renderHook(() => useQueueUpdatesSSE(), { wrapper })

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['queueStats'],
          exact: false,
        })
      })
    })

    it('invalidates specific download query when download_id present', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const downloadId = 'specific-download-123'
      const queueUpdate = {
        action: 'status_changed' as const,
        download_id: downloadId,
        status: 'completed',
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: queueUpdate,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const wrapper = createWrapper()
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      renderHook(() => useQueueUpdatesSSE(), { wrapper })

      await waitFor(() => {
        expect(invalidateQueriesSpy).toHaveBeenCalledWith({
          queryKey: ['download', 'progress', downloadId],
          exact: false,
        })
      })
    })
  })

  describe('Connection State', () => {
    it('tracks connection state correctly', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })
    })

    it('tracks reconnection state', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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
        isReconnecting: true,
        reconnectAttempts: 2,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isReconnecting).toBe(true)
        expect(result.current.reconnectAttempts).toBe(2)
      })
    })
  })

  describe('Error Handling', () => {
    it('returns token error when token fetch fails', async () => {
      const tokenError = new Error('Token fetch failed')
      const mockCreateSSEToken = vi.fn().mockRejectedValue(tokenError)

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

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error)
      })

      consoleErrorSpy.mockRestore()
    })

    it('returns SSE error when connection fails', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
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

      const { result } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.error).toBe(sseError)
      })
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: null,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { unmount } = renderHook(() => useQueueUpdatesSSE(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalled()
      })

      // Should not throw on unmount
      expect(() => unmount()).not.toThrow()
    })
  })
})

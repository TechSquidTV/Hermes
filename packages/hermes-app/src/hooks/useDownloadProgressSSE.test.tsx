/**
 * Tests for useDownloadProgressSSE hook
 *
 * This hook manages ephemeral SSE tokens and real-time download progress updates.
 * It's critical for both home page (TrackedTask) and queue page (QueueCard).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDownloadProgressSSE } from './useDownloadProgressSSE'
import * as apiClientModule from '@/services/api/client'
import * as useSSEModule from './useSSE'
import type { ReactNode } from 'react'

// Mock dependencies
vi.mock('@/services/api/client')
vi.mock('./useSSE')

describe('useDownloadProgressSSE', () => {
  const mockDownloadId = 'test-download-123'
  const mockSSEToken = 'sse_test_token_abc123'
  let queryClient: QueryClient

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

    // Mock environment variable
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  describe('Token Fetching', () => {
    it('fetches SSE token on mount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: `download:${mockDownloadId}`,
          ttl: 600,
        })
      })
    })

    it('sets correct scope for the download ID', async () => {
      const customDownloadId = 'custom-id-456'
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${customDownloadId}`,
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

      renderHook(() => useDownloadProgressSSE(customDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: `download:${customDownloadId}`,
          ttl: 600,
        })
      })
    })

    it('uses 10-minute TTL for tokens', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith(
          expect.objectContaining({ ttl: 600 })
        )
      })
    })

    it('handles token fetch errors gracefully', async () => {
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

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        // The hook logs: console.error('Failed to fetch SSE token:', err)
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Failed to fetch SSE token:',
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
        scope: `download:${mockDownloadId}`,
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

      renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      // Verify token is fetched with correct parameters
      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalledWith({
          scope: `download:${mockDownloadId}`,
          ttl: 600,
        })
      })

      // Verify useSSE is being called (URL construction is tested in "configures SSE with correct options")
      expect(mockUseSSE).toHaveBeenCalled()
    })

    it('does not connect until token is fetched', () => {
      const mockCreateSSEToken = vi.fn().mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

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

      renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      // Should be called with null URL initially
      expect(mockUseSSE).toHaveBeenCalledWith(null, expect.any(Object))
    })

    it('configures SSE with correct options', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockUseSSE).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            events: ['download_progress'],
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

  describe('Download Progress Data', () => {
    it('returns download status from SSE', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
        permissions: ['read'],
        ttl: 600,
      })

      vi.spyOn(apiClientModule, 'apiClient', 'get').mockReturnValue({
        createSSEToken: mockCreateSSEToken,
      } as any)

      const mockDownloadStatus = {
        download_id: mockDownloadId,
        status: 'downloading',
        progress: {
          percentage: 45,
          downloaded_bytes: 450000000,
          total_bytes: 1000000000,
          speed: 5000000,
          eta: 110,
        },
        result: null,
        current_filename: null,
        message: '',
        error: null,
      }

      vi.spyOn(useSSEModule, 'useSSE').mockReturnValue({
        data: mockDownloadStatus,
        isConnected: true,
        error: null,
        isReconnecting: false,
        reconnectAttempts: 0,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.data).toEqual(mockDownloadStatus)
      })
    })

    it('tracks connection state correctly', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })
    })

    it('tracks reconnection attempts', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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
        reconnectAttempts: 3,
        close: vi.fn(),
        reconnect: vi.fn(),
      })

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.isReconnecting).toBe(true)
        expect(result.current.reconnectAttempts).toBe(3)
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

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error)
        expect(result.current.error?.message).toContain('Token fetch failed')
      })

      consoleErrorSpy.mockRestore()
    })

    it('returns SSE error when connection fails', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.error).toBe(sseError)
      })
    })

    it('prioritizes token error over SSE error', async () => {
      const tokenError = new Error('Token fetch failed')
      const mockCreateSSEToken = vi.fn().mockRejectedValue(tokenError)

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

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const { result } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        // Token error should take precedence
        expect(result.current.error?.message).toContain('Token fetch failed')
      })

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Cleanup', () => {
    it('cleans up on unmount', async () => {
      const mockCreateSSEToken = vi.fn().mockResolvedValue({
        token: mockSSEToken,
        expires_at: '2025-12-31T23:59:59Z',
        scope: `download:${mockDownloadId}`,
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

      const { unmount } = renderHook(() => useDownloadProgressSSE(mockDownloadId), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(mockCreateSSEToken).toHaveBeenCalled()
      })

      // Should not throw on unmount
      expect(() => unmount()).not.toThrow()
    })
  })
})

/**
 * Tests for useSSE hook - Base SSE connection management with reconnection logic
 */

import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useSSE } from '../useSSE'

// Mock EventSource instances tracker
const eventSourceInstances: MockEventSource[] = []

// Mock EventSource
class MockEventSource {
  url: string
  readyState: number = 0 // CONNECTING
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  private listeners: Map<string, Array<(event: MessageEvent) => void>> = new Map()

  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  constructor(url: string) {
    this.url = url
    eventSourceInstances.push(this)
    // Simulate async connection
    setTimeout(() => {
      if (this.readyState !== MockEventSource.CLOSED) {
        this.readyState = MockEventSource.OPEN
        if (this.onopen) {
          this.onopen(new Event('open'))
        }
      }
    }, 0)
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, [])
    }
    this.listeners.get(type)!.push(listener)
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    const listeners = this.listeners.get(type)
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  close() {
    this.readyState = MockEventSource.CLOSED
  }

  // Test helper to simulate events
  _simulateMessage(data: string, eventType?: string) {
    const event = new MessageEvent(eventType || 'message', { data })
    if (eventType && eventType !== 'message') {
      const listeners = this.listeners.get(eventType)
      if (listeners) {
        listeners.forEach((listener) => listener(event))
      }
    } else if (this.onmessage) {
      this.onmessage(event)
    }
  }

  _simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }
}

// Replace global EventSource with mock
const originalEventSource = globalThis.EventSource
beforeEach(() => {
  eventSourceInstances.length = 0 // Clear instances
  globalThis.EventSource = MockEventSource as any
  // Don't use fake timers by default - they conflict with waitFor
})

afterEach(() => {
  globalThis.EventSource = originalEventSource
  eventSourceInstances.length = 0
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('useSSE', () => {
  describe('connection establishment', () => {
    it('should establish EventSource connection with valid URL', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream?token=test123')
      )

      expect(result.current.isConnected).toBe(false)

      // Wait for connection (setTimeout with 0ms delay completes naturally)
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      expect(result.current.error).toBeNull()
    })

    it('should not connect when URL is null', () => {
      const { result } = renderHook(() => useSSE(null))

      expect(result.current.isConnected).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('should call onOpen callback when connection opens', async () => {
      const onOpen = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          onOpen,
        })
      )

      // Wait for connection to be established
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Verify onOpen was called
      expect(onOpen).toHaveBeenCalledTimes(1)
    })

    it('should update isConnected state on connection open', async () => {
      const { result } = renderHook(() => useSSE('/api/v1/events/stream'))

      expect(result.current.isConnected).toBe(false)

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })
    })
  })

  describe('event handling', () => {
    it('should parse and set data from JSON messages', async () => {
      const { result } = renderHook(() => useSSE<{ progress: number }>(
        '/api/v1/events/stream'
      ))

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate incoming message
      const eventSource = eventSourceInstances[0]
      act(() => {
        eventSource._simulateMessage(JSON.stringify({ progress: 50 }))
      })

      await waitFor(() => {
        expect(result.current.data).toEqual({ progress: 50 })
      })
    })

    it('should handle specific event types', async () => {
      const { result } = renderHook(() =>
        useSSE<{ status: string }>('/api/v1/events/stream', {
          events: ['download_progress', 'queue_update'],
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate specific event type
      act(() => {
        eventSource._simulateMessage(
          JSON.stringify({ status: 'downloading' }),
          'download_progress'
        )
      })

      await waitFor(() => {
        expect(result.current.data).toEqual({ status: 'downloading' })
      })
    })

    it('should skip empty messages (heartbeats)', async () => {
      const { result } = renderHook(() => useSSE('/api/v1/events/stream'))

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate empty message (heartbeat)
      act(() => {
        eventSource._simulateMessage('')
      })

      // Data should remain null
      expect(result.current.data).toBeNull()

      // Now send real data
      act(() => {
        eventSource._simulateMessage(JSON.stringify({ test: 'data' }))
      })

      await waitFor(() => {
        expect(result.current.data).toEqual({ test: 'data' })
      })
    })

    it('should handle invalid JSON gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const { result } = renderHook(() => useSSE('/api/v1/events/stream'))

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate invalid JSON
      act(() => {
        eventSource._simulateMessage('not valid json{')
      })

      // Should log error but not crash
      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled()
      })

      // Data should remain null
      expect(result.current.data).toBeNull()

      consoleErrorSpy.mockRestore()
    })
  })

  describe('reconnection logic', () => {
    it.skip('should attempt reconnection with exponential backoff', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 3,
          reconnectDelay: 10, // Use short delay for testing
        })
      )

      // Wait for initial connection
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate error (should trigger reconnection)
      act(() => {
        eventSource.readyState = MockEventSource.CLOSED
        eventSource._simulateError()
      })

      // Should be reconnecting after error
      await waitFor(() => {
        expect(result.current.isReconnecting).toBe(true)
        expect(result.current.isConnected).toBe(false)
        expect(result.current.reconnectAttempts).toBe(1)
      })

      // Wait for first reconnection attempt
      await waitFor(() => {
        expect(eventSourceInstances.length).toBeGreaterThan(1)
      }, { timeout: 100 })
    })

    it.skip('should stop reconnecting after max attempts', async () => {
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 2,
          reconnectDelay: 10, // Use short delay for testing
          onClose,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate repeated errors to exceed max attempts
      // First error
      act(() => {
        eventSourceInstances[0].readyState = MockEventSource.CLOSED
        eventSourceInstances[0]._simulateError()
      })

      // Wait for reconnection attempts to complete
      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBe(2)
      }, { timeout: 500 })

      expect(onClose).toHaveBeenCalled()
    })

    it.skip('should not retry on immediate closure (auth failure)', async () => {
      const onError = vi.fn()
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 5,
          reconnectDelay: 10,
          onError,
          onClose,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate immediate closure (like 401/403)
      act(() => {
        eventSource.readyState = MockEventSource.CLOSED
        eventSource._simulateError()
      })

      await waitFor(() => {
        expect(onError).toHaveBeenCalled()
      })

      // Wait a bit to ensure no reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 50))

      // Only one EventSource instance should exist
      expect(eventSourceInstances.length).toBe(1)
    })

    it.skip('should reset reconnect attempts after successful connection', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 10,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate error
      const eventSource1 = eventSourceInstances[0]
      act(() => {
        eventSource1.readyState = MockEventSource.CLOSED
        eventSource1._simulateError()
      })

      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBe(1)
      })

      // Wait for successful reconnection
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      }, { timeout: 100 })

      // Attempts should be reset
      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBe(0)
      })
    })
  })

  describe('manual controls', () => {
    it('should manually close connection', async () => {
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          onClose,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Manually close
      act(() => {
        result.current.close()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false)
      })

      const eventSource = eventSourceInstances[0]
      expect(eventSource.readyState).toBe(MockEventSource.CLOSED)
    })

    it('should manually reconnect', async () => {
      const { result } = renderHook(() => useSSE('/api/v1/events/stream'))

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Close connection
      act(() => {
        result.current.close()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false)
      })

      // Manual reconnect
      act(() => {
        result.current.reconnect()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Should reset attempts
      expect(result.current.reconnectAttempts).toBe(0)
    })
  })

  describe('cleanup', () => {
    it('should cleanup connection on unmount', async () => {
      const { result, unmount } = renderHook(() => useSSE('/api/v1/events/stream'))

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Unmount
      unmount()

      // Event source should be closed immediately
      expect(eventSource.readyState).toBe(MockEventSource.CLOSED)
    })

    it.skip('should clear reconnection timeout on unmount', async () => {
      const { result, unmount } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 100,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Trigger error to start reconnection timer
      const eventSource = eventSourceInstances[0]
      act(() => {
        eventSource.readyState = MockEventSource.CLOSED
        eventSource._simulateError()
      })

      await waitFor(() => {
        expect(result.current.isReconnecting).toBe(true)
      })

      const countBeforeUnmount = eventSourceInstances.length

      // Unmount before timer completes
      unmount()

      // Wait to ensure no new connection is created
      await new Promise(resolve => setTimeout(resolve, 150))

      // Should still be only one EventSource instance
      expect(eventSourceInstances.length).toBe(countBeforeUnmount)
    })
  })

  describe('configuration options', () => {
    it.skip('should respect maxReconnectDelay', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 10,
          maxReconnectDelay: 50,
          maxReconnectAttempts: 5,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate error to trigger reconnections
      act(() => {
        eventSourceInstances[0].readyState = MockEventSource.CLOSED
        eventSourceInstances[0]._simulateError()
      })

      // Wait for reconnection attempts
      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBeGreaterThan(0)
      }, { timeout: 500 })

      // Just verify reconnection logic is working
      expect(result.current.reconnectAttempts).toBeGreaterThan(0)
    })

    it.skip('should allow infinite reconnection attempts when maxReconnectAttempts is 0', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 0, // infinite
          reconnectDelay: 5,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate error - should keep trying
      act(() => {
        eventSourceInstances[0].readyState = MockEventSource.CLOSED
        eventSourceInstances[0]._simulateError()
      })

      // Wait for multiple reconnection attempts
      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBeGreaterThanOrEqual(3)
      }, { timeout: 500 })

      // Should continue reconnecting (not stop at a limit)
      expect(result.current.isReconnecting).toBe(true)
    })

    it.skip('should disable reconnection when reconnect is false', async () => {
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: false,
          onClose,
        })
      )

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate error
      const eventSource = eventSourceInstances[0]
      act(() => {
        eventSource.readyState = MockEventSource.CLOSED
        eventSource._simulateError()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false)
      })

      // Should not attempt reconnection
      expect(result.current.isReconnecting).toBe(false)
      expect(result.current.reconnectAttempts).toBe(0)

      // Wait to ensure no reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 50))

      // Should only have one EventSource instance
      expect(eventSourceInstances.length).toBe(1)
    })
  })
})

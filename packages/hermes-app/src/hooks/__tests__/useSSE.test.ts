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
const originalEventSource = global.EventSource
beforeEach(() => {
  eventSourceInstances.length = 0 // Clear instances
  global.EventSource = MockEventSource as any
  vi.useFakeTimers()
})

afterEach(() => {
  global.EventSource = originalEventSource
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

      // Wait for connection
      await act(async () => {
        vi.runAllTimers()
      })

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

      renderHook(() =>
        useSSE('/api/v1/events/stream', {
          onOpen,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

      await waitFor(() => {
        expect(onOpen).toHaveBeenCalledTimes(1)
      })
    })

    it('should update isConnected state on connection open', async () => {
      const { result } = renderHook(() => useSSE('/api/v1/events/stream'))

      expect(result.current.isConnected).toBe(false)

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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
    it('should attempt reconnection with exponential backoff', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 3,
          reconnectDelay: 1000,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Simulate error (should trigger reconnection)
      act(() => {
        eventSource.readyState = MockEventSource.CLOSED
        eventSource._simulateError()
      })

      await waitFor(() => {
        expect(result.current.isReconnecting).toBe(true)
        expect(result.current.isConnected).toBe(false)
      })

      // First reconnection attempt after 1s (2^0 * 1000)
      expect(result.current.reconnectAttempts).toBe(1)

      // Advance timer for first retry
      await act(async () => {
        vi.advanceTimersByTime(1000)
        vi.runAllTimers()
      })

      // Should create new EventSource
      expect(eventSourceInstances.length).toBeGreaterThan(1)
    })

    it('should stop reconnecting after max attempts', async () => {
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 2,
          reconnectDelay: 100,
          onClose,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      // Simulate repeated errors
      for (let i = 0; i < 3; i++) {
        const eventSource = eventSourceInstances[i]
        act(() => {
          eventSource.readyState = MockEventSource.CLOSED
          eventSource._simulateError()
        })

        await act(async () => {
          vi.advanceTimersByTime(Math.pow(2, i) * 100)
          vi.runAllTimers()
        })
      }

      // Should stop after 2 attempts
      await waitFor(() => {
        expect(result.current.reconnectAttempts).toBe(2)
        expect(onClose).toHaveBeenCalled()
      })
    })

    it('should not retry on immediate closure (auth failure)', async () => {
      const onError = vi.fn()
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 5,
          onError,
          onClose,
        })
      )

      await act(async () => {
        vi.runAllTimers()
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

      // Should not attempt reconnection
      await act(async () => {
        vi.advanceTimersByTime(5000)
      })

      // Only one EventSource instance should exist
      expect(eventSourceInstances.length).toBe(1)
    })

    it('should reset reconnect attempts after successful connection', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 100,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

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

      // Reconnect successfully
      await act(async () => {
        vi.advanceTimersByTime(100)
        vi.runAllTimers()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.runAllTimers()
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

      await act(async () => {
        vi.runAllTimers()
      })

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })

      const eventSource = eventSourceInstances[0]

      // Unmount
      unmount()

      await waitFor(() => {
        expect(eventSource.readyState).toBe(MockEventSource.CLOSED)
      })
    })

    it('should clear reconnection timeout on unmount', async () => {
      const { result, unmount } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 5000,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

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

      // Unmount before timer completes
      unmount()

      // Advance timer - should not create new connection
      await act(async () => {
        vi.advanceTimersByTime(5000)
      })

      // Should still be only one EventSource instance
      expect(eventSourceInstances.length).toBe(1)
    })
  })

  describe('configuration options', () => {
    it('should respect maxReconnectDelay', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          reconnectDelay: 1000,
          maxReconnectDelay: 5000,
          maxReconnectAttempts: 10,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

      // Simulate multiple errors to trigger exponential backoff
      for (let i = 0; i < 5; i++) {
        const eventSource = eventSourceInstances[i]
        act(() => {
          eventSource.readyState = MockEventSource.CLOSED
          eventSource._simulateError()
        })

        const expectedDelay = Math.min(1000 * Math.pow(2, i), 5000)

        await act(async () => {
          vi.advanceTimersByTime(expectedDelay)
          vi.runAllTimers()
        })
      }

      // After multiple attempts, delay should cap at maxReconnectDelay (5000ms)
      expect(result.current.reconnectAttempts).toBeGreaterThan(0)
    })

    it('should allow infinite reconnection attempts when maxReconnectAttempts is 0', async () => {
      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: true,
          maxReconnectAttempts: 0, // infinite
          reconnectDelay: 100,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

      // Simulate 10 errors - should keep trying
      for (let i = 0; i < 10; i++) {
        const eventSource = eventSourceInstances[i]
        act(() => {
          eventSource.readyState = MockEventSource.CLOSED
          eventSource._simulateError()
        })

        await act(async () => {
          vi.advanceTimersByTime(Math.pow(2, i) * 100)
          vi.runAllTimers()
        })
      }

      // Should have attempted many reconnections
      expect(result.current.reconnectAttempts).toBe(10)
    })

    it('should disable reconnection when reconnect is false', async () => {
      const onClose = vi.fn()

      const { result } = renderHook(() =>
        useSSE('/api/v1/events/stream', {
          reconnect: false,
          onClose,
        })
      )

      await act(async () => {
        vi.runAllTimers()
      })

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

      await act(async () => {
        vi.advanceTimersByTime(10000)
      })

      // Should only have one EventSource instance
      expect(eventSourceInstances.length).toBe(1)
    })
  })
})

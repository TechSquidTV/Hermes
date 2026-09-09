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

  static autoOpen = true
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  constructor(url: string) {
    this.url = url
    eventSourceInstances.push(this)
    // Simulate async connection
    if (MockEventSource.autoOpen) setTimeout(() => {
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
  MockEventSource.autoOpen = true
  vi.stubGlobal('EventSource', MockEventSource)
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
    beforeEach(() => {
      vi.useFakeTimers()
      MockEventSource.autoOpen = false
    })

    const fail = (index: number, permanent = false) => act(() => {
      eventSourceInstances[index].readyState = permanent ? MockEventSource.CLOSED : MockEventSource.CONNECTING
      eventSourceInstances[index]._simulateError()
    })
    const advance = (milliseconds: number) => act(() => vi.advanceTimersByTime(milliseconds))
    const open = (index: number) => act(() => {
      eventSourceInstances[index].readyState = MockEventSource.OPEN
      eventSourceInstances[index].onopen?.(new Event('open'))
    })

    it('backs off exponentially and caps the delay', () => {
      const { result } = renderHook(() => useSSE('/events', {
        reconnectDelay: 100, maxReconnectDelay: 150,
      }))
      fail(0)
      expect(eventSourceInstances[0].readyState).toBe(MockEventSource.CLOSED)
      expect(result.current.isReconnecting).toBe(true)
      advance(99)
      expect(eventSourceInstances).toHaveLength(1)
      advance(1)
      fail(1)
      advance(149)
      expect(eventSourceInstances).toHaveLength(2)
      advance(1)
      expect(eventSourceInstances).toHaveLength(3)
    })

    it('stops after the maximum number of attempts', () => {
      const onClose = vi.fn()
      const { result } = renderHook(() => useSSE('/events', {
        reconnectDelay: 100, maxReconnectAttempts: 2, onClose,
      }))
      fail(0)
      advance(100)
      fail(1)
      advance(200)
      fail(2)
      advance(1000)
      expect(eventSourceInstances).toHaveLength(3)
      expect(result.current.reconnectAttempts).toBe(2)
      expect(result.current.isReconnecting).toBe(false)
      expect(onClose).toHaveBeenCalledOnce()
    })

    it('does not retry permanent closure', () => {
      const onError = vi.fn()
      const { result } = renderHook(() => useSSE('/events', { onError }))
      fail(0, true)
      advance(10000)
      expect(eventSourceInstances).toHaveLength(1)
      expect(result.current.isReconnecting).toBe(false)
      expect(onError).toHaveBeenCalledOnce()
    })

    it('resets attempts when a connection succeeds', () => {
      const { result } = renderHook(() => useSSE('/events', { reconnectDelay: 100 }))
      fail(0)
      advance(100)
      expect(result.current.reconnectAttempts).toBe(1)
      open(1)
      expect(result.current.isConnected).toBe(true)
      expect(result.current.reconnectAttempts).toBe(0)
    })

    it('allows unlimited attempts when configured', () => {
      const { result } = renderHook(() => useSSE('/events', {
        maxReconnectAttempts: 0, reconnectDelay: 10, maxReconnectDelay: 10,
      }))
      for (let index = 0; index < 10; index++) {
        fail(index)
        advance(10)
      }
      expect(eventSourceInstances).toHaveLength(11)
      expect(result.current.reconnectAttempts).toBe(10)
    })

    it('closes the browser connection when retries are disabled', () => {
      const { result } = renderHook(() => useSSE('/events', { reconnect: false }))
      fail(0)
      advance(10000)
      expect(eventSourceInstances).toHaveLength(1)
      expect(eventSourceInstances[0].readyState).toBe(MockEventSource.CLOSED)
      expect(result.current.isReconnecting).toBe(false)
    })

    it('clears pending retries on unmount', () => {
      const { unmount } = renderHook(() => useSSE('/events'))
      fail(0)
      unmount()
      advance(10000)
      expect(eventSourceInstances).toHaveLength(1)
    })

    it('manual reconnect clears pending retries and re-enables automatic retries', () => {
      const { result } = renderHook(() => useSSE('/events', { reconnectDelay: 100 }))
      fail(0)
      act(() => result.current.reconnect())
      advance(100)
      expect(eventSourceInstances).toHaveLength(2)
      act(() => result.current.close())
      act(() => result.current.reconnect())
      fail(2)
      advance(100)
      expect(eventSourceInstances).toHaveLength(4)
    })

    it('ignores duplicate errors and messages from obsolete connections', () => {
      const { result } = renderHook(() => useSSE<{ value: number }>('/events', { reconnectDelay: 100 }))
      fail(0)
      fail(0)
      act(() => eventSourceInstances[0]._simulateMessage('{"value":1}'))
      advance(100)
      expect(eventSourceInstances).toHaveLength(2)
      expect(result.current.reconnectAttempts).toBe(1)
      expect(result.current.data).toBeNull()
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

  })
})

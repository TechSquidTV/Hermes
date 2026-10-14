import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSSEToken } from './useSSEToken'
import { apiClient } from '@/services/api/client'
import type { components } from '@/types/api.generated'

vi.mock('@/services/api/client', () => ({ apiClient: { createSSEToken: vi.fn() } }))
const token = (name: string, seconds = 61): components['schemas']['SSETokenResponse'] => ({
  token: name,
  expiresAt: new Date(Date.now() + seconds * 1000).toISOString(),
  scope: 'queue',
  permissions: ['read'],
  ttl: seconds,
})
beforeEach(() => {
  vi.useFakeTimers()
  vi.resetAllMocks()
})
afterEach(() => {
  vi.useRealTimers()
})
const advance = async (ms = 0) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

describe('SSE token recovery', () => {
  it('renews using the server expiry before the requested TTL', async () => {
    vi.mocked(apiClient.createSSEToken)
      .mockResolvedValueOnce(token('first'))
      .mockResolvedValueOnce(token('second', 600))
    const { result } = renderHook(() => useSSEToken('queue', 600))
    await advance()
    expect(result.current.token).toBe('first')
    await advance(1000)
    expect(result.current.token).toBe('second')
    expect(apiClient.createSSEToken).toHaveBeenCalledTimes(2)
  })

  it('retries initial failures with backoff without a remount', async () => {
    vi.mocked(apiClient.createSSEToken)
      .mockRejectedValueOnce(new Error('Offline'))
      .mockRejectedValueOnce(new Error('Still offline'))
      .mockResolvedValue(token('recovered', 600))
    const { result } = renderHook(() => useSSEToken('queue', 600))
    await advance()
    expect(result.current.error?.message).toBe('Offline')
    await advance(1000)
    expect(result.current.error?.message).toBe('Still offline')
    await advance(1999)
    expect(apiClient.createSSEToken).toHaveBeenCalledTimes(2)
    await advance(1)
    expect(result.current.token).toBe('recovered')
    expect(result.current.error).toBeNull()
  })

  it('keeps an established token during renewal failure and then recovers', async () => {
    vi.mocked(apiClient.createSSEToken)
      .mockResolvedValueOnce(token('first'))
      .mockRejectedValueOnce(new Error('Unavailable'))
      .mockResolvedValue(token('replacement', 600))
    const { result } = renderHook(() => useSSEToken('queue', 600))
    await advance()
    await advance(1000)
    expect(result.current.token).toBe('first')
    expect(result.current.error?.message).toBe('Unavailable')
    await advance(1000)
    expect(result.current.token).toBe('replacement')
  })

  it('cancels pending retries and the request signal when unmounted', async () => {
    vi.mocked(apiClient.createSSEToken).mockRejectedValue(new Error('Offline'))
    const { unmount } = renderHook(() => useSSEToken('queue', 600))
    await advance()
    const signal = vi.mocked(apiClient.createSSEToken).mock.calls[0]?.[1]
    unmount()
    expect(signal?.aborted).toBe(true)
    await advance(60_000)
    expect(apiClient.createSSEToken).toHaveBeenCalledOnce()
  })

  it('never exposes a token from a previous scope', async () => {
    vi.mocked(apiClient.createSSEToken)
      .mockResolvedValueOnce(token('old', 600))
      .mockImplementationOnce(() => new Promise(() => {}))
    const { result, rerender } = renderHook(({ scope }) => useSSEToken(scope, 600), {
      initialProps: { scope: 'queue' },
    })
    await advance()
    expect(result.current.token).toBe('old')
    rerender({ scope: 'stats' })
    expect(result.current.token).toBeNull()
  })
})

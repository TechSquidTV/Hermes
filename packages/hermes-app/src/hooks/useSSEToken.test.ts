import { renderHook, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSSEToken } from './useSSEToken';
import { apiClient } from '@/services/api/client';

vi.mock('@/services/api/client', () => ({
  apiClient: {
    createSSEToken: vi.fn(),
  },
}));

describe('useSSEToken', () => {
  const mockCreateSSEToken = vi.mocked(apiClient.createSSEToken);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renews the token before the ttl expires', async () => {
    mockCreateSSEToken
      .mockResolvedValueOnce({
        token: 'sse_first',
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 61,
      })
      .mockResolvedValueOnce({
        token: 'sse_second',
        expires_at: '2025-12-31T23:59:59Z',
        scope: 'queue',
        permissions: ['read'],
        ttl: 61,
      });

    const { result } = renderHook(() => useSSEToken('queue', 600, 'Failed to fetch SSE token:'));

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.token).toBe('sse_first');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(mockCreateSSEToken).toHaveBeenCalledTimes(2);
    expect(result.current.token).toBe('sse_second');
  });
});

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/services/api/client'
import { getQueueQueryKey, useQueueData } from '../useQueueData'

vi.mock('@/services/api/client', () => ({
  apiClient: {
    getDownloadQueue: vi.fn(),
  },
}))

const mockGetDownloadQueue = vi.mocked(apiClient.getDownloadQueue)

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient, children })
}

describe('useQueueData helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDownloadQueue.mockResolvedValue({
      totalItems: 0,
      pending: 0,
      active: 0,
      completed: 0,
      failed: 0,
      items: [],
    })
  })

  it('keys queue data by effective request filter and pagination', () => {
    expect(getQueueQueryKey('downloading', 'active', 50, 20)).toEqual([
      'queue',
      'downloading',
      50,
      20,
    ])
  })

  it('normalizes ignored filters to avoid duplicate cache entries', () => {
    expect(getQueueQueryKey('all', 'history')).toEqual([
      'queue',
      'completed',
      20,
      0,
    ])
    expect(getQueueQueryKey('failed', 'history')).toEqual(
      getQueueQueryKey('all', 'history')
    )
    expect(getQueueQueryKey('downloading', 'all')).toEqual([
      'queue',
      'all',
      20,
      0,
    ])
  })

  it('loads queue data with the effective status filter', async () => {
    const wrapper = createWrapper()

    const { result } = renderHook(
      () =>
        useQueueData({
          statusFilter: 'failed',
          viewMode: 'history',
          limit: 10,
          offset: 5,
        }),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(mockGetDownloadQueue).toHaveBeenCalledWith('completed', 10, 5)
    expect(result.current.data?.items).toEqual([])
  })
})

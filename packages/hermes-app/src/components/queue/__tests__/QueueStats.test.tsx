import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { apiClient } from '@/services/api/client'
import { QueueStats } from '../QueueStats'

vi.mock('@/hooks/useStatsSSE', () => ({ useStatsSSE: () => ({}) }))
afterEach(() => vi.restoreAllMocks())

it('shows total attempts and converts the API success fraction into a percentage', async () => {
  vi.spyOn(apiClient, 'getApiStats').mockResolvedValue({
    period: 'week', totalDownloads: 4, successfulDownloads: 3, failedDownloads: 1,
    successRate: 0.75, averageDownloadTime: 2, totalBandwidthUsed: 300,
    peakHour: 12, totalStorageUsed: 300,
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><QueueStats /></QueryClientProvider>)
  expect(await screen.findByText('75.0%')).toBeInTheDocument()
  expect(screen.getByText('4')).toBeInTheDocument()
  client.clear()
})

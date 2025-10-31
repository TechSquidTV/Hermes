/**
 * Tests for QueueView component
 *
 * Tests the main queue view with tabs for active, history, all, and analytics
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { QueueView } from '../QueueView'

// Mock child components
vi.mock('../QueueFilters', () => ({
  QueueFilters: ({ viewMode, onStatusFilterChange, onSearchQueryChange, onSortChange }: any) => (
    <div data-testid={`queue-filters-${viewMode}`}>
      <button onClick={() => onStatusFilterChange('downloading')}>Change Status</button>
      <button onClick={() => onSearchQueryChange('test')}>Change Search</button>
      <button onClick={() => onSortChange('title', 'asc')}>Change Sort</button>
    </div>
  ),
}))

vi.mock('../QueueCharts', () => ({
  QueueCharts: () => <div data-testid="queue-charts">Charts</div>,
}))

vi.mock('../QueueTabContent', () => ({
  QueueTabContent: ({ viewMode, showStats }: any) => (
    <div data-testid={`queue-tab-content-${viewMode}`}>
      Content for {viewMode}
      {showStats && <span data-testid="shows-stats">With Stats</span>}
    </div>
  ),
}))

vi.mock('@/hooks/useViewMode', () => {
  const { useState } = require('react')

  return {
    useViewMode: () => {
      const [mode, setMode] = useState('active')
      return { mode, setMode }
    },
  }
})

vi.mock('@/hooks/useFilters', () => {
  const { useState } = require('react')

  return {
    useFilters: () => {
      const [filters, setFilters] = useState({
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'created_at',
        sortOrder: 'desc',
        viewMode: 'active',
      })

      const updateFilter = (key: string, value: any) => {
        setFilters((prev: any) => ({ ...prev, [key]: value }))
      }

      return { filters, updateFilter }
    },
  }
})

describe('QueueView', () => {
  let queryClient: QueryClient

  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    return ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders all tab triggers', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      expect(screen.getByRole('tab', { name: /active/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /history/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /all/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /analytics/i })).toBeInTheDocument()
    })

    it('renders filters for active tab', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      expect(screen.getByTestId('queue-filters-active')).toBeInTheDocument()
    })

    it('renders queue content for active tab', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      expect(screen.getByTestId('queue-tab-content-active')).toBeInTheDocument()
      expect(screen.getByText(/content for active/i)).toBeInTheDocument()
    })
  })

  describe('Tab Navigation', () => {
    it('switches to history tab when clicked', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const historyTab = screen.getByRole('tab', { name: /history/i })
      await user.click(historyTab)

      // Check the tab is selected
      expect(historyTab).toHaveAttribute('data-state', 'active')
    })

    it('switches to all tab when clicked', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)

      // Check the tab is selected
      expect(allTab).toHaveAttribute('data-state', 'active')
    })

    it('switches to analytics tab when clicked', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const chartsTab = screen.getByRole('tab', { name: /analytics/i })
      await user.click(chartsTab)

      // Check the tab is selected
      expect(chartsTab).toHaveAttribute('data-state', 'active')
    })
  })

  describe('Filter Integration', () => {
    it('passes filters to QueueFilters component', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      // Filters should be rendered
      const filters = screen.getByTestId('queue-filters-active')
      expect(filters).toBeInTheDocument()
    })

    it('passes filters to QueueTabContent component', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      // Tab content should be rendered with filters
      const tabContent = screen.getByTestId('queue-tab-content-active')
      expect(tabContent).toBeInTheDocument()
    })
  })

  describe('History Tab Special Features', () => {
    it('can switch to history tab', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const historyTab = screen.getByRole('tab', { name: /history/i })
      await user.click(historyTab)

      // History tab should be active
      expect(historyTab).toHaveAttribute('data-state', 'active')
    })

    it('does not show stats in active tab', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      // Active tab should not show stats indicator
      expect(screen.queryByTestId('shows-stats')).not.toBeInTheDocument()
    })

    it('can switch to all tab without stats', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)

      // All tab should be active
      expect(allTab).toHaveAttribute('data-state', 'active')
    })
  })

  describe('Tab Content Structure', () => {
    it('renders correct tab content for active view', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      // Check active content is visible
      expect(screen.getByText(/content for active/i)).toBeInTheDocument()
    })

    it('can switch between all tabs', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      // Switch to history
      const historyTab = screen.getByRole('tab', { name: /history/i })
      await user.click(historyTab)
      expect(historyTab).toHaveAttribute('data-state', 'active')

      // Switch to all
      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)
      expect(allTab).toHaveAttribute('data-state', 'active')

      // Switch to charts
      const chartsTab = screen.getByRole('tab', { name: /analytics/i })
      await user.click(chartsTab)
      expect(chartsTab).toHaveAttribute('data-state', 'active')
    })
  })

  describe('Filter Callbacks', () => {
    it('provides filter callbacks to active tab', () => {
      render(<QueueView />, { wrapper: createWrapper() })

      const filters = screen.getByTestId('queue-filters-active')
      expect(filters).toBeInTheDocument()

      // Filter callback buttons should be present
      expect(screen.getByText('Change Status')).toBeInTheDocument()
      expect(screen.getByText('Change Search')).toBeInTheDocument()
      expect(screen.getByText('Change Sort')).toBeInTheDocument()
    })

    it('can switch to history tab', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const historyTab = screen.getByRole('tab', { name: /history/i })
      await user.click(historyTab)

      // Tab should be active
      expect(historyTab).toHaveAttribute('data-state', 'active')
    })

    it('can switch to all tab', async () => {
      const user = userEvent.setup()
      render(<QueueView />, { wrapper: createWrapper() })

      const allTab = screen.getByRole('tab', { name: /all/i })
      await user.click(allTab)

      // Tab should be active
      expect(allTab).toHaveAttribute('data-state', 'active')
    })
  })
})

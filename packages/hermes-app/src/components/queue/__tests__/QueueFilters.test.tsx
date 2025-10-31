/**
 * Tests for QueueFilters component
 *
 * Tests the filter controls including status filters, search, and contextual sort labels
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { QueueFilters } from '../QueueFilters'

describe('QueueFilters', () => {
  const defaultProps = {
    statusFilter: 'all',
    onStatusFilterChange: vi.fn(),
    searchQuery: '',
    onSearchQueryChange: vi.fn(),
    viewMode: 'active' as const,
    sortBy: 'date' as const,
    sortOrder: 'desc' as const,
    onSortChange: vi.fn(),
  }

  describe('Rendering', () => {
    it('renders search input', () => {
      render(<QueueFilters {...defaultProps} />)

      expect(screen.getByPlaceholderText(/search downloads/i)).toBeInTheDocument()
    })

    it('renders status filter badges', () => {
      render(<QueueFilters {...defaultProps} viewMode="active" />)

      expect(screen.getByText('All')).toBeInTheDocument()
      expect(screen.getByText('Downloading')).toBeInTheDocument()
      expect(screen.getByText('Queued')).toBeInTheDocument()
      expect(screen.getByText('Processing')).toBeInTheDocument()
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })

    it('renders different status filters for history view', () => {
      render(<QueueFilters {...defaultProps} viewMode="history" />)

      expect(screen.getByText('All')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.queryByText('Downloading')).not.toBeInTheDocument()
    })

    it('renders sort dropdown button', () => {
      render(<QueueFilters {...defaultProps} />)

      expect(screen.getByRole('button', { name: /date.*newest first/i })).toBeInTheDocument()
    })
  })

  describe('Sort Label Display - Date', () => {
    it('displays "Newest First" for date desc', () => {
      render(<QueueFilters {...defaultProps} sortBy="date" sortOrder="desc" />)

      expect(screen.getByRole('button', { name: /date.*newest first/i })).toBeInTheDocument()
    })

    it('displays "Oldest First" for date asc', () => {
      render(<QueueFilters {...defaultProps} sortBy="date" sortOrder="asc" />)

      expect(screen.getByRole('button', { name: /date.*oldest first/i })).toBeInTheDocument()
    })
  })

  describe('Sort Label Display - Size', () => {
    it('displays "Largest First" for size desc', () => {
      render(<QueueFilters {...defaultProps} sortBy="size" sortOrder="desc" />)

      expect(screen.getByRole('button', { name: /size.*largest first/i })).toBeInTheDocument()
    })

    it('displays "Smallest First" for size asc', () => {
      render(<QueueFilters {...defaultProps} sortBy="size" sortOrder="asc" />)

      expect(screen.getByRole('button', { name: /size.*smallest first/i })).toBeInTheDocument()
    })
  })

  describe('Sort Label Display - Title', () => {
    it('displays "Z-A" for title desc', () => {
      render(<QueueFilters {...defaultProps} sortBy="title" sortOrder="desc" />)

      expect(screen.getByRole('button', { name: /title.*z-a/i })).toBeInTheDocument()
    })

    it('displays "A-Z" for title asc', () => {
      render(<QueueFilters {...defaultProps} sortBy="title" sortOrder="asc" />)

      expect(screen.getByRole('button', { name: /title.*a-z/i })).toBeInTheDocument()
    })
  })

  describe('Sort Label Display - Status', () => {
    it('displays "Z-A" for status desc', () => {
      render(<QueueFilters {...defaultProps} sortBy="status" sortOrder="desc" />)

      expect(screen.getByRole('button', { name: /status.*z-a/i })).toBeInTheDocument()
    })

    it('displays "A-Z" for status asc', () => {
      render(<QueueFilters {...defaultProps} sortBy="status" sortOrder="asc" />)

      expect(screen.getByRole('button', { name: /status.*a-z/i })).toBeInTheDocument()
    })
  })

  describe('Sort Dropdown Menu Options', () => {
    it('shows contextual labels for all sort options', async () => {
      const user = userEvent.setup()
      render(<QueueFilters {...defaultProps} />)

      // Open dropdown
      const sortButton = screen.getByRole('button', { name: /date.*newest first/i })
      await user.click(sortButton)

      // Date options (use getAllByText since they appear in button and menu)
      expect(screen.getAllByText(/date.*newest first/i).length).toBeGreaterThan(0)
      expect(screen.getByText(/date.*oldest first/i)).toBeInTheDocument()

      // Size options
      expect(screen.getByText(/size.*largest first/i)).toBeInTheDocument()
      expect(screen.getByText(/size.*smallest first/i)).toBeInTheDocument()

      // Title options
      expect(screen.getByText(/title.*z-a/i)).toBeInTheDocument()
      expect(screen.getByText(/title.*a-z/i)).toBeInTheDocument()

      // Status options
      expect(screen.getByText(/status.*z-a/i)).toBeInTheDocument()
      expect(screen.getByText(/status.*a-z/i)).toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('calls onSearchQueryChange when typing in search', async () => {
      const user = userEvent.setup()
      const onSearchQueryChange = vi.fn()
      render(<QueueFilters {...defaultProps} onSearchQueryChange={onSearchQueryChange} />)

      const searchInput = screen.getByPlaceholderText(/search downloads/i)
      await user.type(searchInput, 'test')

      expect(onSearchQueryChange).toHaveBeenCalled()
    })

    it('calls onStatusFilterChange when clicking status badge', async () => {
      const user = userEvent.setup()
      const onStatusFilterChange = vi.fn()
      render(<QueueFilters {...defaultProps} onStatusFilterChange={onStatusFilterChange} />)

      const downloadingBadge = screen.getByText('Downloading')
      await user.click(downloadingBadge)

      expect(onStatusFilterChange).toHaveBeenCalledWith('downloading')
    })

    it('calls onSortChange when clicking sort option', async () => {
      const user = userEvent.setup()
      const onSortChange = vi.fn()
      render(<QueueFilters {...defaultProps} onSortChange={onSortChange} />)

      // Open dropdown
      const sortButton = screen.getByRole('button', { name: /date.*newest first/i })
      await user.click(sortButton)

      // Click size largest first
      const sizeOption = screen.getByText(/size.*largest first/i)
      await user.click(sizeOption)

      expect(onSortChange).toHaveBeenCalledWith('size', 'desc')
    })

    it('highlights active status filter', () => {
      render(<QueueFilters {...defaultProps} statusFilter="downloading" />)

      const downloadingBadge = screen.getByText('Downloading')
      // The active badge should have the 'default' variant
      expect(downloadingBadge).toBeInTheDocument()
    })

    it('shows current sort selection in button', async () => {
      const user = userEvent.setup()
      render(<QueueFilters {...defaultProps} sortBy="size" sortOrder="desc" />)

      // Button should display current sort and order
      expect(screen.getByRole('button', { name: /size.*largest first/i })).toBeInTheDocument()

      // Open dropdown and verify all options are present
      const sortButton = screen.getByRole('button', { name: /size.*largest first/i })
      await user.click(sortButton)

      // Verify dropdown has options with contextual labels
      expect(screen.getAllByText(/size.*largest first/i).length).toBeGreaterThan(0)
      expect(screen.getByText(/size.*smallest first/i)).toBeInTheDocument()
    })
  })

  describe('View Mode Status Filters', () => {
    it('shows active-specific filters in active view', () => {
      render(<QueueFilters {...defaultProps} viewMode="active" />)

      expect(screen.getByText('Downloading')).toBeInTheDocument()
      expect(screen.getByText('Queued')).toBeInTheDocument()
      expect(screen.queryByText('Completed')).not.toBeInTheDocument()
    })

    it('shows history-specific filters in history view', () => {
      render(<QueueFilters {...defaultProps} viewMode="history" />)

      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.queryByText('Downloading')).not.toBeInTheDocument()
      expect(screen.queryByText('Queued')).not.toBeInTheDocument()
    })

    it('shows all filters in all view', () => {
      render(<QueueFilters {...defaultProps} viewMode="all" />)

      expect(screen.getByText('Downloading')).toBeInTheDocument()
      expect(screen.getByText('Queued')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has accessible search input', () => {
      render(<QueueFilters {...defaultProps} />)

      const searchInput = screen.getByPlaceholderText(/search downloads/i)
      expect(searchInput).toBeInTheDocument()
      expect(searchInput.tagName).toBe('INPUT')
    })

    it('has accessible dropdown button', () => {
      render(<QueueFilters {...defaultProps} />)

      const sortButton = screen.getByRole('button', { name: /date.*newest first/i })
      expect(sortButton).toBeInTheDocument()
    })

    it('status badges are clickable', async () => {
      const user = userEvent.setup()
      const onStatusFilterChange = vi.fn()
      render(<QueueFilters {...defaultProps} onStatusFilterChange={onStatusFilterChange} />)

      const allBadge = screen.getByText('All')
      expect(allBadge).toHaveClass('cursor-pointer')

      await user.click(allBadge)
      expect(onStatusFilterChange).toHaveBeenCalledWith('all')
    })
  })
})

/**
 * Tests for usePagination hook
 *
 * Tests pagination state management, navigation, and page number calculation.
 */

import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePagination } from '../usePagination'

describe('usePagination', () => {
  describe('Initial State', () => {
    it('initializes with default values', () => {
      const { result } = renderHook(() => usePagination())

      expect(result.current.currentPage).toBe(1)
      expect(result.current.pageSize).toBe(20)
      expect(result.current.totalItems).toBe(0)
      expect(result.current.totalPages).toBe(0)
      expect(result.current.hasNextPage).toBe(false)
      expect(result.current.hasPreviousPage).toBe(false)
    })

    it('accepts custom initial page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100 })
      )

      expect(result.current.currentPage).toBe(3)
    })

    it('accepts custom page size', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPageSize: 50 })
      )

      expect(result.current.pageSize).toBe(50)
    })

    it('accepts total items', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.totalItems).toBe(100)
      expect(result.current.totalPages).toBe(5)
    })
  })

  describe('Total Pages Calculation', () => {
    it('calculates total pages correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.totalPages).toBe(5)
    })

    it('rounds up partial pages', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 101, initialPageSize: 20 })
      )

      expect(result.current.totalPages).toBe(6)
    })

    it('handles zero items', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 0 })
      )

      expect(result.current.totalPages).toBe(0)
    })

    it('handles single page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 15, initialPageSize: 20 })
      )

      expect(result.current.totalPages).toBe(1)
    })
  })

  describe('Indices Calculation', () => {
    it('calculates start and end indices for first page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.startIndex).toBe(0)
      expect(result.current.endIndex).toBe(20)
      expect(result.current.showingStart).toBe(1)
      expect(result.current.showingEnd).toBe(20)
    })

    it('calculates indices for middle page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.startIndex).toBe(40)
      expect(result.current.endIndex).toBe(60)
      expect(result.current.showingStart).toBe(41)
      expect(result.current.showingEnd).toBe(60)
    })

    it('handles last page with fewer items', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 95, initialPageSize: 20 })
      )

      expect(result.current.startIndex).toBe(80)
      expect(result.current.endIndex).toBe(95)
      expect(result.current.showingStart).toBe(81)
      expect(result.current.showingEnd).toBe(95)
    })
  })

  describe('Navigation Flags', () => {
    it('hasNextPage is true when not on last page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 1, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.hasNextPage).toBe(true)
      expect(result.current.hasPreviousPage).toBe(false)
      expect(result.current.isFirstPage).toBe(true)
      expect(result.current.isLastPage).toBe(false)
    })

    it('hasPreviousPage is true when not on first page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.hasNextPage).toBe(true)
      expect(result.current.hasPreviousPage).toBe(true)
      expect(result.current.isFirstPage).toBe(false)
      expect(result.current.isLastPage).toBe(false)
    })

    it('both flags are correct on last page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.hasNextPage).toBe(false)
      expect(result.current.hasPreviousPage).toBe(true)
      expect(result.current.isFirstPage).toBe(false)
      expect(result.current.isLastPage).toBe(true)
    })
  })

  describe('goToPage', () => {
    it('navigates to valid page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToPage(3)
      })

      expect(result.current.currentPage).toBe(3)
    })

    it('ignores navigation to page 0', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToPage(0)
      })

      expect(result.current.currentPage).toBe(1)
    })

    it('ignores navigation beyond total pages', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToPage(10)
      })

      expect(result.current.currentPage).toBe(1)
    })
  })

  describe('goToNextPage', () => {
    it('navigates to next page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToNextPage()
      })

      expect(result.current.currentPage).toBe(2)
    })

    it('does not navigate past last page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToNextPage()
      })

      expect(result.current.currentPage).toBe(5)
    })
  })

  describe('goToPreviousPage', () => {
    it('navigates to previous page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToPreviousPage()
      })

      expect(result.current.currentPage).toBe(2)
    })

    it('does not navigate before first page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToPreviousPage()
      })

      expect(result.current.currentPage).toBe(1)
    })
  })

  describe('goToFirstPage', () => {
    it('navigates to first page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToFirstPage()
      })

      expect(result.current.currentPage).toBe(1)
    })
  })

  describe('goToLastPage', () => {
    it('navigates to last page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.goToLastPage()
      })

      expect(result.current.currentPage).toBe(5)
    })
  })

  describe('changePageSize', () => {
    it('changes page size', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.changePageSize(50)
      })

      expect(result.current.pageSize).toBe(50)
      expect(result.current.totalPages).toBe(2)
    })

    it('resets to first page when changing size', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      act(() => {
        result.current.changePageSize(50)
      })

      expect(result.current.currentPage).toBe(1)
    })
  })

  describe('getOffset', () => {
    it('calculates offset for first page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.getOffset()).toBe(0)
    })

    it('calculates offset for middle page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.getOffset()).toBe(40)
    })
  })

  describe('getPageNumbers', () => {
    it('returns all pages when total <= maxVisible', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 60, initialPageSize: 20 })
      )

      expect(result.current.getPageNumbers(5)).toEqual([1, 2, 3])
    })

    it('shows ellipsis when pages exceed maxVisible', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 200, initialPageSize: 20 })
      )

      const pages = result.current.getPageNumbers(5)
      expect(pages).toContain('...')
    })

    it('shows first page with ellipsis when far from start', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 8, totalItems: 200, initialPageSize: 20 })
      )

      const pages = result.current.getPageNumbers(5)
      expect(pages[0]).toBe(1)
      expect(pages[1]).toBe('...')
    })

    it('shows last page with ellipsis when far from end', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 200, initialPageSize: 20 })
      )

      const pages = result.current.getPageNumbers(5)
      expect(pages[pages.length - 1]).toBe(10)
      expect(pages[pages.length - 2]).toBe('...')
    })

    it('handles edge case at start', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 1, totalItems: 200, initialPageSize: 20 })
      )

      const pages = result.current.getPageNumbers(5)
      expect(pages[0]).toBe(1)
      expect(pages).toContain('...')
      expect(pages[pages.length - 1]).toBe(10)
    })

    it('handles edge case at end', () => {
      const { result } = renderHook(() =>
        usePagination({
          initialPage: 10,
          totalItems: 200,
          initialPageSize: 20,
        })
      )

      const pages = result.current.getPageNumbers(5)
      expect(pages[0]).toBe(1)
      expect(pages).toContain('...')
      expect(pages[pages.length - 1]).toBe(10)
    })

    it('uses default maxVisible of 5', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 200, initialPageSize: 20 })
      )

      const pages = result.current.getPageNumbers()
      expect(pages.length).toBeGreaterThan(0)
    })
  })

  describe('Complex Navigation', () => {
    it('handles complete navigation sequence', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 20 })
      )

      // Start on page 1
      expect(result.current.currentPage).toBe(1)

      // Go to next page
      act(() => {
        result.current.goToNextPage()
      })
      expect(result.current.currentPage).toBe(2)

      // Go to last page
      act(() => {
        result.current.goToLastPage()
      })
      expect(result.current.currentPage).toBe(5)

      // Go to previous page
      act(() => {
        result.current.goToPreviousPage()
      })
      expect(result.current.currentPage).toBe(4)

      // Go to first page
      act(() => {
        result.current.goToFirstPage()
      })
      expect(result.current.currentPage).toBe(1)

      // Go to specific page
      act(() => {
        result.current.goToPage(3)
      })
      expect(result.current.currentPage).toBe(3)
    })

    it('recalculates total pages when page size changes', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100, initialPageSize: 20 })
      )

      expect(result.current.totalPages).toBe(5)

      act(() => {
        result.current.changePageSize(10)
      })

      expect(result.current.totalPages).toBe(10)
      expect(result.current.currentPage).toBe(1)
    })
  })
})

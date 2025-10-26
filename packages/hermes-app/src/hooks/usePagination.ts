import { useState, useCallback, useMemo } from 'react'

interface UsePaginationOptions {
  initialPage?: number
  initialPageSize?: number
  totalItems?: number
}

export function usePagination(options: UsePaginationOptions = {}) {
  const {
    initialPage = 1,
    initialPageSize = 20,
    totalItems = 0
  } = options

  const [currentPage, setCurrentPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)

  const totalPages = useMemo(() => {
    return Math.ceil(totalItems / pageSize)
  }, [totalItems, pageSize])

  const startIndex = useMemo(() => {
    return (currentPage - 1) * pageSize
  }, [currentPage, pageSize])

  const endIndex = useMemo(() => {
    return Math.min(startIndex + pageSize, totalItems)
  }, [startIndex, pageSize, totalItems])

  const hasNextPage = currentPage < totalPages
  const hasPreviousPage = currentPage > 1

  const goToPage = useCallback((page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }, [totalPages])

  const goToNextPage = useCallback(() => {
    if (hasNextPage) {
      setCurrentPage(prev => prev + 1)
    }
  }, [hasNextPage])

  const goToPreviousPage = useCallback(() => {
    if (hasPreviousPage) {
      setCurrentPage(prev => prev - 1)
    }
  }, [hasPreviousPage])

  const goToFirstPage = useCallback(() => {
    setCurrentPage(1)
  }, [])

  const goToLastPage = useCallback(() => {
    setCurrentPage(totalPages)
  }, [totalPages])

  const changePageSize = useCallback((newSize: number) => {
    setPageSize(newSize)
    setCurrentPage(1) // Reset to first page when changing page size
  }, [])

  const getOffset = useCallback(() => {
    return (currentPage - 1) * pageSize
  }, [currentPage, pageSize])

  const getPageNumbers = useCallback((maxVisible: number = 5) => {
    const pages: (number | string)[] = []

    if (totalPages <= maxVisible) {
      // Show all pages if total is less than max visible
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // Calculate range around current page
      const half = Math.floor(maxVisible / 2)
      let start = Math.max(1, currentPage - half)
      let end = Math.min(totalPages, currentPage + half)

      // Adjust range if we're near the edges
      if (end - start + 1 < maxVisible) {
        if (start === 1) {
          end = Math.min(totalPages, start + maxVisible - 1)
        } else if (end === totalPages) {
          start = Math.max(1, end - maxVisible + 1)
        }
      }

      // Add first page and ellipsis if needed
      if (start > 1) {
        pages.push(1)
        if (start > 2) {
          pages.push('...')
        }
      }

      // Add range of pages
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }

      // Add last page and ellipsis if needed
      if (end < totalPages) {
        if (end < totalPages - 1) {
          pages.push('...')
        }
        pages.push(totalPages)
      }
    }

    return pages
  }, [currentPage, totalPages])

  return {
    // Current state
    currentPage,
    pageSize,
    totalItems,
    totalPages,

    // Navigation
    goToPage,
    goToNextPage,
    goToPreviousPage,
    goToFirstPage,
    goToLastPage,

    // State
    hasNextPage,
    hasPreviousPage,
    startIndex,
    endIndex,

    // Configuration
    changePageSize,

    // Utilities
    getOffset,
    getPageNumbers,

    // Computed properties
    showingStart: startIndex + 1,
    showingEnd: endIndex,
    isFirstPage: currentPage === 1,
    isLastPage: currentPage === totalPages,
  }
}



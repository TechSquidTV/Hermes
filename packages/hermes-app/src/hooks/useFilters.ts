import { useState, useMemo } from 'react'
import type { DownloadStatus, DownloadResult } from '@/types'

// Type guard to check if result is a proper DownloadResult
const isDownloadResult = (result: unknown): result is DownloadResult => {
  return typeof result === 'object' && result !== null && ('url' in result || 'title' in result || 'extractor' in result)
}

export type ViewMode = 'active' | 'history' | 'all'

export interface FilterState {
  statusFilter: string
  searchQuery: string
  viewMode: ViewMode
  sortBy: 'date' | 'size' | 'title' | 'status'
  sortOrder: 'asc' | 'desc'
}

export interface UseFiltersOptions {
  initialViewMode?: ViewMode
  initialStatusFilter?: string
  initialSortBy?: FilterState['sortBy']
  initialSortOrder?: FilterState['sortOrder']
}

export function useFilters(options: UseFiltersOptions = {}) {
  const {
    initialViewMode = 'active',
    initialStatusFilter = 'all',
    initialSortBy = 'date',
    initialSortOrder = 'desc',
  } = options

  const [filters, setFilters] = useState<FilterState>({
    statusFilter: initialStatusFilter,
    searchQuery: '',
    viewMode: initialViewMode,
    sortBy: initialSortBy,
    sortOrder: initialSortOrder,
  })

  const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const resetFilters = () => {
    setFilters({
      statusFilter: 'all',
      searchQuery: '',
      viewMode: initialViewMode,
      sortBy: initialSortBy,
      sortOrder: initialSortOrder,
    })
  }

  // Get available status filters based on view mode
  const availableStatusFilters = useMemo(() => {
    if (filters.viewMode === 'active') {
      return [
        { value: 'all', label: 'All' },
        { value: 'downloading', label: 'Downloading' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'failed', label: 'Failed' },
      ]
    } else if (filters.viewMode === 'history') {
      return [
        { value: 'all', label: 'All' },
        { value: 'completed', label: 'Completed' },
      ]
    } else {
      return [
        { value: 'all', label: 'All' },
        { value: 'downloading', label: 'Downloading' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'completed', label: 'Completed' },
        { value: 'failed', label: 'Failed' },
      ]
    }
  }, [filters.viewMode])

  return {
    filters,
    updateFilter,
    resetFilters,
    availableStatusFilters,
  }
}

// Filter and sort downloads based on current filters
export function useFilteredDownloads<T extends DownloadStatus>(
  downloads: T[],
  filters: FilterState
) {
  return useMemo(() => {
    const filtered = downloads.filter(download => {
      // Status filter
      if (filters.statusFilter !== 'all' && download.status !== filters.statusFilter) {
        return false
      }

      // Search filter
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        const result = isDownloadResult(download.result) ? download.result : undefined
        const title = result?.title?.toLowerCase() || ''
        const url = result?.url?.toLowerCase() || ''

        if (!title.includes(query) && !url.includes(query)) {
          return false
        }
      }

      return true
    })

    // Sort
    filtered.sort((a, b) => {
      let aValue: string | number, bValue: string | number

      switch (filters.sortBy) {
        case 'date': {
          // Use createdAt timestamp for proper chronological sorting
          aValue = new Date(a.createdAt).getTime()
          bValue = new Date(b.createdAt).getTime()
          break
        }
        case 'size': {
          const aResult = isDownloadResult(a.result) ? a.result : undefined
          const bResult = isDownloadResult(b.result) ? b.result : undefined
          aValue = aResult?.fileSize || 0
          bValue = bResult?.fileSize || 0
          break
        }
        case 'title': {
          const aResult = isDownloadResult(a.result) ? a.result : undefined
          const bResult = isDownloadResult(b.result) ? b.result : undefined
          aValue = aResult?.title || ''
          bValue = bResult?.title || ''
          break
        }
        case 'status':
          aValue = a.status
          bValue = b.status
          break
        default:
          return 0
      }

      if (filters.sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
      }
    })

    return filtered
  }, [downloads, filters])
}

import { useState, useMemo } from 'react'
import type { components } from '@/types/api.generated'

type DownloadStatus = components["schemas"]["DownloadStatus"]


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
        const title = (download.result && typeof download.result === 'object' && 'title' in download.result && (download.result as any).title)
          ? (download.result as any).title?.toLowerCase() || ''
          : ''
        const url = (download.result && typeof download.result === 'object' && 'url' in download.result && (download.result as any).url)
          ? (download.result as any).url?.toLowerCase() || ''
          : ''

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
        case 'date':
          // Use download_id as a fallback since there's no created_at
          aValue = a.download_id
          bValue = b.download_id
          break
        case 'size':
          aValue = (a.result && typeof a.result === 'object' && 'file_size' in a.result) ? (a.result as any).file_size || 0 : 0
          bValue = (b.result && typeof b.result === 'object' && 'file_size' in b.result) ? (b.result as any).file_size || 0 : 0
          break
        case 'title':
          aValue = (a.result && typeof a.result === 'object' && 'title' in a.result) ? (a.result as any).title || '' : ''
          bValue = (b.result && typeof b.result === 'object' && 'title' in b.result) ? (b.result as any).title || '' : ''
          break
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

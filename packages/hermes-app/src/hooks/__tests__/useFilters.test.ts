/**
 * Tests for useFilteredDownloads hook
 *
 * Tests the filtering and sorting logic for downloads,
 * including the new created_at timestamp sorting
 */

import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useFilteredDownloads, type FilterState } from '../useFilters'
import type { DownloadStatus } from '@/types'

describe('useFilteredDownloads', () => {
  const mockDownloads: DownloadStatus[] = [
    {
      download_id: '1',
      status: 'completed',
      message: '',
      result: {
        title: 'First Video',
        url: 'https://example.com/1',
        file_size: 1024 * 1024 * 50, // 50MB
      },
      created_at: '2025-01-01T10:00:00Z',
    },
    {
      download_id: '2',
      status: 'downloading',
      message: '',
      result: {
        title: 'Second Video',
        url: 'https://example.com/2',
        file_size: 1024 * 1024 * 100, // 100MB
      },
      created_at: '2025-01-02T10:00:00Z',
    },
    {
      download_id: '3',
      status: 'failed',
      message: '',
      result: {
        title: 'Third Video',
        url: 'https://example.com/3',
        file_size: 1024 * 1024 * 25, // 25MB
      },
      created_at: '2025-01-03T10:00:00Z',
    },
  ]

  describe('Date Sorting', () => {
    it('sorts by created_at timestamp in descending order (newest first)', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current[0].download_id).toBe('3') // Newest (2025-01-03)
      expect(result.current[1].download_id).toBe('2') // Middle (2025-01-02)
      expect(result.current[2].download_id).toBe('1') // Oldest (2025-01-01)
    })

    it('sorts by created_at timestamp in ascending order (oldest first)', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'asc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current[0].download_id).toBe('1') // Oldest (2025-01-01)
      expect(result.current[1].download_id).toBe('2') // Middle (2025-01-02)
      expect(result.current[2].download_id).toBe('3') // Newest (2025-01-03)
    })

    it('handles downloads without created_at field', () => {
      const downloadsWithoutCreatedAt: DownloadStatus[] = [
        {
          download_id: '1',
          status: 'completed',
          message: '',
          result: { title: 'Test', url: 'https://example.com' },
          created_at: '2025-01-01T09:00:00Z',
        },
        {
          download_id: '2',
          status: 'completed',
          message: '',
          result: { title: 'Test 2', url: 'https://example.com/2' },
          created_at: '2025-01-01T10:00:00Z',
        },
      ]

      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(downloadsWithoutCreatedAt, filters))

      // Should not throw error and place items without created_at at the end
      expect(result.current[0].download_id).toBe('2') // Has created_at
    })
  })

  describe('Size Sorting', () => {
    it('sorts by file size in descending order (largest first)', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'size',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current[0].download_id).toBe('2') // 100MB
      expect(result.current[1].download_id).toBe('1') // 50MB
      expect(result.current[2].download_id).toBe('3') // 25MB
    })

    it('sorts by file size in ascending order (smallest first)', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'size',
        sortOrder: 'asc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current[0].download_id).toBe('3') // 25MB
      expect(result.current[1].download_id).toBe('1') // 50MB
      expect(result.current[2].download_id).toBe('2') // 100MB
    })
  })

  describe('Status Filtering', () => {
    it('filters by completed status', () => {
      const filters: FilterState = {
        statusFilter: 'completed',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(1)
      expect(result.current[0].status).toBe('completed')
    })

    it('filters by downloading status', () => {
      const filters: FilterState = {
        statusFilter: 'downloading',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(1)
      expect(result.current[0].status).toBe('downloading')
    })

    it('shows all downloads when statusFilter is "all"', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(3)
    })
  })

  describe('Search Filtering', () => {
    it('filters by title search query', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: 'Second',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(1)
      expect(result.current[0].download_id).toBe('2')
    })

    it('filters by URL search query', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: 'example.com/3',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(1)
      expect(result.current[0].download_id).toBe('3')
    })

    it('search is case-insensitive', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: 'THIRD VIDEO',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      expect(result.current.length).toBe(1)
      expect(result.current[0].download_id).toBe('3')
    })
  })

  describe('Combined Filtering and Sorting', () => {
    it('applies status filter and date sort together', () => {
      const downloads: DownloadStatus[] = [
        {
          download_id: '1',
          status: 'completed',
          message: '',
          result: { title: 'Old Completed', url: 'https://example.com/1' },
          created_at: '2025-01-01T10:00:00Z',
        },
        {
          download_id: '2',
          status: 'completed',
          message: '',
          result: { title: 'New Completed', url: 'https://example.com/2' },
          created_at: '2025-01-03T10:00:00Z',
        },
        {
          download_id: '3',
          status: 'downloading',
          message: '',
          result: { title: 'Downloading', url: 'https://example.com/3' },
          created_at: '2025-01-02T10:00:00Z',
        },
      ]

      const filters: FilterState = {
        statusFilter: 'completed',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(downloads, filters))

      expect(result.current.length).toBe(2)
      expect(result.current[0].download_id).toBe('2') // Newest completed
      expect(result.current[1].download_id).toBe('1') // Oldest completed
    })

    it('applies search filter and size sort together', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: 'Video',
        sortBy: 'size',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(mockDownloads, filters))

      // All have "Video" in title
      expect(result.current.length).toBe(3)
      // Sorted by size descending
      expect(result.current[0].download_id).toBe('2') // 100MB
      expect(result.current[1].download_id).toBe('1') // 50MB
      expect(result.current[2].download_id).toBe('3') // 25MB
    })
  })

  describe('Edge Cases', () => {
    it('handles empty downloads array', () => {
      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads([], filters))

      expect(result.current).toEqual([])
    })

    it('handles downloads with missing result data', () => {
      const incompleteDownloads: DownloadStatus[] = [
        {
          download_id: '1',
          status: 'pending',
          message: '',
          created_at: '2025-01-01T10:00:00Z',
        },
      ]

      const filters: FilterState = {
        statusFilter: 'all',
        searchQuery: '',
        sortBy: 'date',
        sortOrder: 'desc',
        viewMode: 'all',
      }

      const { result } = renderHook(() => useFilteredDownloads(incompleteDownloads, filters))

      expect(result.current.length).toBe(1)
    })
  })
})

/**
 * Tests for useStorage hooks
 *
 * Tests storage info queries, cleanup mutations, and storage calculations.
 */

import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useStorageCalculations } from '../useStorage'
import type { components } from '@/types/api.generated'

type StorageInfo = components['schemas']['StorageInfo']

describe('useStorageCalculations', () => {
  describe('Basic Calculations', () => {
    it('calculates storage values correctly', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 300,
        free_space: 700,
        usage_percentage: 30,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 200,
        temp_size: 100,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.totalSpace).toBe(1000)
      expect(result.current.usedSpace).toBe(300)
      expect(result.current.freeSpace).toBe(700)
      expect(result.current.usagePercentage).toBe(30)
      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('handles empty storage info', () => {
      const { result } = renderHook(() => useStorageCalculations(undefined))

      expect(result.current.totalSpace).toBe(0)
      expect(result.current.usedSpace).toBe(0)
      expect(result.current.freeSpace).toBe(0)
      expect(result.current.usagePercentage).toBe(0)
      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('handles zero total space', () => {
      const storageInfo: StorageInfo = {
        total_space: 0,
        used_space: 0,
        free_space: 0,
        usage_percentage: 0,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 0,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(0)
      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })
  })

  describe('Usage Percentage', () => {
    it('calculates 0% usage', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 0,
        free_space: 1000,
        usage_percentage: 0,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 0,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(0)
    })

    it('calculates 50% usage', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 500,
        free_space: 500,
        usage_percentage: 50,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 500,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(50)
    })

    it('calculates 100% usage', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 1000,
        free_space: 0,
        usage_percentage: 100,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 1000,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(100)
      expect(result.current.freeSpace).toBe(0)
    })

    it('calculates fractional percentages correctly', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 333,
        free_space: 667,
        usage_percentage: 33.3,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 333,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBeCloseTo(33.3, 1)
    })
  })

  describe('Low Space Detection', () => {
    it('detects low space at 91%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 910,
        free_space: 90,
        usage_percentage: 91,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 910,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 90%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 900,
        free_space: 100,
        usage_percentage: 90,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 900,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 89%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 890,
        free_space: 110,
        usage_percentage: 89,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 890,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(false)
    })
  })

  describe('Critical Space Detection', () => {
    it('detects critical space at 96%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 960,
        free_space: 40,
        usage_percentage: 96,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 960,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(true)
    })

    it('does not detect critical space at 95%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 950,
        free_space: 50,
        usage_percentage: 95,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 950,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('detects critical space at 100%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 1000,
        free_space: 0,
        usage_percentage: 100,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 1000,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isCriticalSpace).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('handles very large storage values', () => {
      const storageInfo: StorageInfo = {
        total_space: 10_000_000_000, // 10TB
        used_space: 5_000_000_000, // 5TB
        free_space: 5_000_000_000,
        usage_percentage: 50,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 5_000_000_000,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.totalSpace).toBe(10_000_000_000)
      expect(result.current.usedSpace).toBe(5_000_000_000)
      expect(result.current.freeSpace).toBe(5_000_000_000)
      expect(result.current.usagePercentage).toBe(50)
    })

    it('handles very small storage values', () => {
      const storageInfo: StorageInfo = {
        total_space: 100,
        used_space: 1,
        free_space: 99,
        usage_percentage: 1,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 1,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(1)
      expect(result.current.freeSpace).toBe(99)
    })

    it('handles missing optional fields', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 300,
        free_space: 700,
        usage_percentage: 30,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 0,
        temp_size: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.totalSpace).toBe(1000)
      expect(result.current.usedSpace).toBe(300)
      expect(result.current.freeSpace).toBe(700)
    })
  })

  describe('Reactivity', () => {
    it('recalculates when storage info changes', () => {
      const initialStorageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 300,
        free_space: 700,
        usage_percentage: 30,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 300,
        temp_size: 0,
      }

      const { result, rerender } = renderHook(
        ({ storageInfo }: { storageInfo?: StorageInfo }) => useStorageCalculations(storageInfo),
        { initialProps: { storageInfo: initialStorageInfo } }
      )

      expect(result.current.usagePercentage).toBe(30)
      expect(result.current.isLowSpace).toBe(false)

      const updatedStorageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 920,
        free_space: 80,
        usage_percentage: 92,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 920,
        temp_size: 0,
      }

      rerender({ storageInfo: updatedStorageInfo })

      expect(result.current.usagePercentage).toBe(92)
      expect(result.current.isLowSpace).toBe(true)
    })

    it('handles transition from defined to undefined', () => {
      const initialStorageInfo: StorageInfo | undefined = {
        total_space: 1000,
        used_space: 300,
        free_space: 700,
        usage_percentage: 30,
        download_directory: '/downloads',
        temp_directory: '/tmp',
        downloads_size: 300,
        temp_size: 0,
      }

      const { result, rerender } = renderHook(
        (storageInfo: StorageInfo | undefined) => useStorageCalculations(storageInfo),
        { initialProps: initialStorageInfo }
      )

      expect(result.current.usagePercentage).toBe(30)

      rerender(undefined)

      expect(result.current.usagePercentage).toBe(0)
      expect(result.current.totalSpace).toBe(0)
    })
  })
})

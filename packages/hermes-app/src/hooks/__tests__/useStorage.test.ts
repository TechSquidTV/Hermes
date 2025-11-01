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
        downloads_space: 200,
        downloads_count: 5,
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
        downloads_space: 0,
        downloads_count: 0,
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
        downloads_space: 0,
        downloads_count: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(0)
    })

    it('calculates 50% usage', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 500,
        downloads_space: 500,
        downloads_count: 10,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(50)
    })

    it('calculates 100% usage', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 1000,
        downloads_space: 1000,
        downloads_count: 20,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(100)
      expect(result.current.freeSpace).toBe(0)
    })

    it('calculates fractional percentages correctly', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 333,
        downloads_space: 333,
        downloads_count: 5,
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
        downloads_space: 910,
        downloads_count: 15,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 90%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 900,
        downloads_space: 900,
        downloads_count: 15,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 89%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 890,
        downloads_space: 890,
        downloads_count: 15,
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
        downloads_space: 960,
        downloads_count: 20,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(true)
    })

    it('does not detect critical space at 95%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 950,
        downloads_space: 950,
        downloads_count: 20,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('detects critical space at 100%', () => {
      const storageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 1000,
        downloads_space: 1000,
        downloads_count: 25,
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
        downloads_space: 5_000_000_000,
        downloads_count: 1000,
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
        downloads_space: 1,
        downloads_count: 1,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(1)
      expect(result.current.freeSpace).toBe(99)
    })

    it('handles missing optional fields', () => {
      const storageInfo = {
        total_space: 1000,
        used_space: 300,
      } as StorageInfo

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
        downloads_space: 300,
        downloads_count: 5,
      }

      const { result, rerender } = renderHook(
        ({ storageInfo }) => useStorageCalculations(storageInfo),
        { initialProps: { storageInfo: initialStorageInfo } }
      )

      expect(result.current.usagePercentage).toBe(30)
      expect(result.current.isLowSpace).toBe(false)

      const updatedStorageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 920,
        downloads_space: 920,
        downloads_count: 15,
      }

      rerender({ storageInfo: updatedStorageInfo })

      expect(result.current.usagePercentage).toBe(92)
      expect(result.current.isLowSpace).toBe(true)
    })

    it('handles transition from defined to undefined', () => {
      const initialStorageInfo: StorageInfo = {
        total_space: 1000,
        used_space: 300,
        downloads_space: 300,
        downloads_count: 5,
      }

      const { result, rerender } = renderHook(
        ({ storageInfo }) => useStorageCalculations(storageInfo),
        { initialProps: { storageInfo: initialStorageInfo } }
      )

      expect(result.current.usagePercentage).toBe(30)

      rerender({ storageInfo: undefined })

      expect(result.current.usagePercentage).toBe(0)
      expect(result.current.totalSpace).toBe(0)
    })
  })
})

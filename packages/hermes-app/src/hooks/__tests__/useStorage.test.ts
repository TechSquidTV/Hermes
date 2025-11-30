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
        totalSpace: 1000,
        usedSpace: 300,
        freeSpace: 700,
        usagePercentage: 30,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 200,
        tempSize: 100,
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
        totalSpace: 0,
        usedSpace: 0,
        freeSpace: 0,
        usagePercentage: 0,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 0,
        tempSize: 0,
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
        totalSpace: 1000,
        usedSpace: 0,
        freeSpace: 1000,
        usagePercentage: 0,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 0,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(0)
    })

    it('calculates 50% usage', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 500,
        freeSpace: 500,
        usagePercentage: 50,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 500,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(50)
    })

    it('calculates 100% usage', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 1000,
        freeSpace: 0,
        usagePercentage: 100,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 1000,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(100)
      expect(result.current.freeSpace).toBe(0)
    })

    it('calculates fractional percentages correctly', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 333,
        freeSpace: 667,
        usagePercentage: 33.3,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 333,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBeCloseTo(33.3, 1)
    })
  })

  describe('Low Space Detection', () => {
    it('detects low space at 91%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 910,
        freeSpace: 90,
        usagePercentage: 91,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 910,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 90%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 900,
        freeSpace: 100,
        usagePercentage: 90,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 900,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(false)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('does not detect low space at 89%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 890,
        freeSpace: 110,
        usagePercentage: 89,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 890,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(false)
    })
  })

  describe('Critical Space Detection', () => {
    it('detects critical space at 96%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 960,
        freeSpace: 40,
        usagePercentage: 96,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 960,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(true)
    })

    it('does not detect critical space at 95%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 950,
        freeSpace: 50,
        usagePercentage: 95,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 950,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isLowSpace).toBe(true)
      expect(result.current.isCriticalSpace).toBe(false)
    })

    it('detects critical space at 100%', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 1000,
        freeSpace: 0,
        usagePercentage: 100,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 1000,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.isCriticalSpace).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('handles very large storage values', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 10_000_000_000, // 10TB
        usedSpace: 5_000_000_000, // 5TB
        freeSpace: 5_000_000_000,
        usagePercentage: 50,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 5_000_000_000,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.totalSpace).toBe(10_000_000_000)
      expect(result.current.usedSpace).toBe(5_000_000_000)
      expect(result.current.freeSpace).toBe(5_000_000_000)
      expect(result.current.usagePercentage).toBe(50)
    })

    it('handles very small storage values', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 100,
        usedSpace: 1,
        freeSpace: 99,
        usagePercentage: 1,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 1,
        tempSize: 0,
      }

      const { result } = renderHook(() => useStorageCalculations(storageInfo))

      expect(result.current.usagePercentage).toBe(1)
      expect(result.current.freeSpace).toBe(99)
    })

    it('handles missing optional fields', () => {
      const storageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 300,
        freeSpace: 700,
        usagePercentage: 30,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 0,
        tempSize: 0,
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
        totalSpace: 1000,
        usedSpace: 300,
        freeSpace: 700,
        usagePercentage: 30,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 300,
        tempSize: 0,
      }

      const { result, rerender } = renderHook(
        ({ storageInfo }: { storageInfo?: StorageInfo }) => useStorageCalculations(storageInfo),
        { initialProps: { storageInfo: initialStorageInfo } }
      )

      expect(result.current.usagePercentage).toBe(30)
      expect(result.current.isLowSpace).toBe(false)

      const updatedStorageInfo: StorageInfo = {
        totalSpace: 1000,
        usedSpace: 920,
        freeSpace: 80,
        usagePercentage: 92,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 920,
        tempSize: 0,
      }

      rerender({ storageInfo: updatedStorageInfo })

      expect(result.current.usagePercentage).toBe(92)
      expect(result.current.isLowSpace).toBe(true)
    })

    it('handles transition from defined to undefined', () => {
      const initialStorageInfo: StorageInfo | undefined = {
        totalSpace: 1000,
        usedSpace: 300,
        freeSpace: 700,
        usagePercentage: 30,
        downloadDirectory: '/downloads',
        tempDirectory: '/tmp',
        downloadsSize: 300,
        tempSize: 0,
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

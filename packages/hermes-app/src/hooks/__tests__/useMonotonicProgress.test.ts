/**
 * Tests for useMonotonicProgress hook
 *
 * Tests the monotonically increasing progress tracking to prevent
 * progress bars from moving backwards due to SSE timing issues.
 */

import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useMonotonicProgress } from '../useMonotonicProgress'

describe('useMonotonicProgress', () => {
  describe('Initial State', () => {
    it('starts at 0 progress', () => {
      const { result } = renderHook(() =>
        useMonotonicProgress(null, undefined)
      )

      expect(result.current).toBe(0)
    })

    it('accepts initial progress value', () => {
      const { result } = renderHook(() =>
        useMonotonicProgress(25, 'downloading')
      )

      expect(result.current).toBe(25)
    })
  })

  describe('Queued Status', () => {
    it('resets progress to 0 when status is queued', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 50, status: 'downloading' }
        }
      )

      expect(result.current).toBe(50)

      // Change to queued status
      rerender({ progress: 0, status: 'queued' })

      expect(result.current).toBe(0)
    })

    it('resets even if progress value is higher', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 75, status: 'downloading' }
        }
      )

      expect(result.current).toBe(75)

      // Queued with high progress value (shouldn't happen but test defensive behavior)
      rerender({ progress: 100, status: 'queued' })

      expect(result.current).toBe(0)
    })
  })

  describe('Downloading Status', () => {
    it('tracks maximum progress during downloading', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 10 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(10)

      // Progress increases
      rerender({ progress: 25, status: 'downloading' })
      expect(result.current).toBe(25)

      rerender({ progress: 50, status: 'downloading' })
      expect(result.current).toBe(50)
    })

    it('prevents progress from going backwards', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 50 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(50)

      // Out-of-order SSE event with lower progress
      rerender({ progress: 30, status: 'downloading' })

      // Progress should not decrease
      expect(result.current).toBe(50)
    })

    it('handles null progress values', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 50 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(50)

      // Null progress (e.g., SSE reconnection)
      rerender({ progress: null, status: 'downloading' })

      // Should keep last known progress
      expect(result.current).toBe(50)
    })

    it('handles undefined progress values', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 40 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(40)

      // Undefined progress
      rerender({ progress: undefined, status: 'downloading' })

      // Should keep last known progress
      expect(result.current).toBe(40)
    })
  })

  describe('Processing Status', () => {
    it('tracks maximum progress during processing', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 60, status: 'processing' }
        }
      )

      expect(result.current).toBe(60)

      // Progress increases
      rerender({ progress: 80, status: 'processing' })
      expect(result.current).toBe(80)
    })

    it('prevents backwards progress during processing', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 80, status: 'processing' }
        }
      )

      expect(result.current).toBe(80)

      // Lower progress value
      rerender({ progress: 70, status: 'processing' })

      // Should not decrease
      expect(result.current).toBe(80)
    })
  })

  describe('Completed/Failed Status', () => {
    it('maintains progress when completed', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 100, status: 'downloading' }
        }
      )

      expect(result.current).toBe(100)

      // Status changes to completed
      rerender({ progress: 100, status: 'completed' })

      // Should maintain progress
      expect(result.current).toBe(100)
    })

    it('keeps last known progress when failed', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 75, status: 'downloading' }
        }
      )

      expect(result.current).toBe(75)

      // Download fails
      rerender({ progress: 75, status: 'failed' })

      // Should keep last progress
      expect(result.current).toBe(75)
    })
  })

  describe('Complex Scenarios', () => {
    it('handles complete download lifecycle with jitter', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 0, status: 'queued' }
        }
      )

      // Start: queued
      expect(result.current).toBe(0)

      // Begin downloading
      rerender({ progress: 10, status: 'downloading' })
      expect(result.current).toBe(10)

      // Progress with jitter (out of order)
      rerender({ progress: 25, status: 'downloading' })
      expect(result.current).toBe(25)

      rerender({ progress: 20, status: 'downloading' }) // Jitter - backwards
      expect(result.current).toBe(25) // Should not decrease

      rerender({ progress: 50, status: 'downloading' })
      expect(result.current).toBe(50)

      rerender({ progress: 45, status: 'downloading' }) // More jitter
      expect(result.current).toBe(50) // Should not decrease

      // Processing
      rerender({ progress: 75, status: 'processing' })
      expect(result.current).toBe(75)

      // Complete - maintains last known progress from processing phase
      rerender({ progress: 100, status: 'completed' })
      expect(result.current).toBe(75) // Keeps last max from active phase
    })

    it('handles SSE reconnection with null progress', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 60 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(60)

      // SSE disconnects, progress becomes null
      rerender({ progress: null, status: 'downloading' })
      expect(result.current).toBe(60) // Maintains last value

      // SSE reconnects with slightly lower value (old event)
      rerender({ progress: 55, status: 'downloading' })
      expect(result.current).toBe(60) // Does not go backwards

      // Continues with correct progress
      rerender({ progress: 80, status: 'downloading' })
      expect(result.current).toBe(80)
    })

    it('handles rapid status changes', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 0, status: 'queued' }
        }
      )

      expect(result.current).toBe(0)

      // Rapid progression
      rerender({ progress: 10, status: 'downloading' })
      rerender({ progress: 30, status: 'downloading' })
      rerender({ progress: 50, status: 'processing' })
      rerender({ progress: 100, status: 'completed' })

      // Maintains last max from active phase (50 from processing)
      expect(result.current).toBe(50)
    })
  })

  describe('Edge Cases', () => {
    it('handles 0 progress during downloading', () => {
      const { result } = renderHook(() =>
        useMonotonicProgress(0, 'downloading')
      )

      expect(result.current).toBe(0)
    })

    it('handles 100 progress during downloading', () => {
      const { result } = renderHook(() =>
        useMonotonicProgress(100, 'downloading')
      )

      expect(result.current).toBe(100)
    })

    it('handles undefined status', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }: { progress: number | null | undefined; status: string | undefined }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 50 as number | null | undefined, status: 'downloading' as string | undefined }
        }
      )

      expect(result.current).toBe(50)

      // Undefined status
      rerender({ progress: 40, status: undefined })

      // Should maintain last known progress
      expect(result.current).toBe(50)
    })

    it('handles unknown status values', () => {
      const { result, rerender } = renderHook(
        ({ progress, status }) => useMonotonicProgress(progress, status),
        {
          initialProps: { progress: 75, status: 'downloading' }
        }
      )

      expect(result.current).toBe(75)

      // Unknown status (future-proofing)
      rerender({ progress: 60, status: 'unknown-status' as any })

      // Should maintain progress for unknown status
      expect(result.current).toBe(75)
    })
  })
})

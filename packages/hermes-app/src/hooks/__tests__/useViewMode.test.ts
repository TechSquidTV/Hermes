/**
 * Tests for useViewMode hook
 *
 * Tests the view mode state management for switching between
 * active, history, all, and charts views.
 */

import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useViewMode, type ViewMode } from '../useViewMode'

describe('useViewMode', () => {
  describe('Initial State', () => {
    it('defaults to active mode', () => {
      const { result } = renderHook(() => useViewMode())

      expect(result.current.mode).toBe('active')
      expect(result.current.isActive).toBe(true)
      expect(result.current.isHistory).toBe(false)
      expect(result.current.isAll).toBe(false)
      expect(result.current.isCharts).toBe(false)
    })

    it('accepts custom initial mode', () => {
      const { result } = renderHook(() =>
        useViewMode({ initialMode: 'history' })
      )

      expect(result.current.mode).toBe('history')
      expect(result.current.isActive).toBe(false)
      expect(result.current.isHistory).toBe(true)
    })

    it('accepts all as initial mode', () => {
      const { result } = renderHook(() => useViewMode({ initialMode: 'all' }))

      expect(result.current.mode).toBe('all')
      expect(result.current.isAll).toBe(true)
    })

    it('accepts charts as initial mode', () => {
      const { result } = renderHook(() =>
        useViewMode({ initialMode: 'charts' })
      )

      expect(result.current.mode).toBe('charts')
      expect(result.current.isCharts).toBe(true)
    })
  })

  describe('Mode Changes', () => {
    it('switches from active to history', () => {
      const { result } = renderHook(() => useViewMode())

      expect(result.current.mode).toBe('active')

      act(() => {
        result.current.setMode('history')
      })

      expect(result.current.mode).toBe('history')
      expect(result.current.isHistory).toBe(true)
      expect(result.current.isActive).toBe(false)
    })

    it('switches to all mode', () => {
      const { result } = renderHook(() => useViewMode())

      act(() => {
        result.current.setMode('all')
      })

      expect(result.current.mode).toBe('all')
      expect(result.current.isAll).toBe(true)
      expect(result.current.isActive).toBe(false)
    })

    it('switches to charts mode', () => {
      const { result } = renderHook(() => useViewMode())

      act(() => {
        result.current.setMode('charts')
      })

      expect(result.current.mode).toBe('charts')
      expect(result.current.isCharts).toBe(true)
      expect(result.current.isActive).toBe(false)
    })

    it('handles multiple mode switches', () => {
      const { result } = renderHook(() => useViewMode())

      act(() => {
        result.current.setMode('history')
      })
      expect(result.current.mode).toBe('history')

      act(() => {
        result.current.setMode('all')
      })
      expect(result.current.mode).toBe('all')

      act(() => {
        result.current.setMode('active')
      })
      expect(result.current.mode).toBe('active')
    })
  })

  describe('Callback', () => {
    it('calls onModeChange callback when mode changes', () => {
      const onModeChange = vi.fn()
      const { result } = renderHook(() => useViewMode({ onModeChange }))

      act(() => {
        result.current.setMode('history')
      })

      expect(onModeChange).toHaveBeenCalledWith('history')
      expect(onModeChange).toHaveBeenCalledTimes(1)
    })

    it('does not call callback on initial render', () => {
      const onModeChange = vi.fn()
      renderHook(() =>
        useViewMode({ initialMode: 'history', onModeChange })
      )

      expect(onModeChange).not.toHaveBeenCalled()
    })

    it('calls callback for each mode change', () => {
      const onModeChange = vi.fn()
      const { result } = renderHook(() => useViewMode({ onModeChange }))

      act(() => {
        result.current.setMode('history')
      })
      act(() => {
        result.current.setMode('all')
      })
      act(() => {
        result.current.setMode('charts')
      })

      expect(onModeChange).toHaveBeenCalledTimes(3)
      expect(onModeChange).toHaveBeenNthCalledWith(1, 'history')
      expect(onModeChange).toHaveBeenNthCalledWith(2, 'all')
      expect(onModeChange).toHaveBeenNthCalledWith(3, 'charts')
    })

    it('works without onModeChange callback', () => {
      const { result } = renderHook(() => useViewMode())

      expect(() => {
        act(() => {
          result.current.setMode('history')
        })
      }).not.toThrow()

      expect(result.current.mode).toBe('history')
    })
  })

  describe('Boolean Helpers', () => {
    it('updates all boolean helpers when mode changes', () => {
      const { result } = renderHook(() => useViewMode())

      // Active mode
      expect(result.current.isActive).toBe(true)
      expect(result.current.isHistory).toBe(false)
      expect(result.current.isAll).toBe(false)
      expect(result.current.isCharts).toBe(false)

      // Switch to history
      act(() => {
        result.current.setMode('history')
      })
      expect(result.current.isActive).toBe(false)
      expect(result.current.isHistory).toBe(true)
      expect(result.current.isAll).toBe(false)
      expect(result.current.isCharts).toBe(false)

      // Switch to all
      act(() => {
        result.current.setMode('all')
      })
      expect(result.current.isActive).toBe(false)
      expect(result.current.isHistory).toBe(false)
      expect(result.current.isAll).toBe(true)
      expect(result.current.isCharts).toBe(false)

      // Switch to charts
      act(() => {
        result.current.setMode('charts')
      })
      expect(result.current.isActive).toBe(false)
      expect(result.current.isHistory).toBe(false)
      expect(result.current.isAll).toBe(false)
      expect(result.current.isCharts).toBe(true)
    })
  })

  describe('Callback Stability', () => {
    it('maintains callback reference stability', () => {
      const onModeChange = vi.fn()
      const { result, rerender } = renderHook(() =>
        useViewMode({ onModeChange })
      )

      const firstSetMode = result.current.setMode

      rerender()

      const secondSetMode = result.current.setMode

      expect(firstSetMode).toBe(secondSetMode)
    })

    it('updates callback reference when onModeChange changes', () => {
      const firstCallback = vi.fn()
      const { result, rerender } = renderHook(
        ({ callback }: { callback?: (mode: ViewMode) => void }) =>
          useViewMode({ onModeChange: callback }),
        { initialProps: { callback: firstCallback } }
      )

      const firstSetMode = result.current.setMode

      const secondCallback = vi.fn()
      rerender({ callback: secondCallback })

      const secondSetMode = result.current.setMode

      // Callback should update when onModeChange changes
      expect(firstSetMode).not.toBe(secondSetMode)

      act(() => {
        result.current.setMode('history')
      })

      expect(secondCallback).toHaveBeenCalledWith('history')
      expect(firstCallback).not.toHaveBeenCalled()
    })
  })
})

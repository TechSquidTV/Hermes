import { useState, useCallback } from 'react'

export type ViewMode = 'active' | 'history' | 'all' | 'charts'

interface UseViewModeOptions {
  initialMode?: ViewMode
  onModeChange?: (mode: ViewMode) => void
}

export function useViewMode(options: UseViewModeOptions = {}) {
  const { initialMode = 'active', onModeChange } = options
  const [mode, setMode] = useState<ViewMode>(initialMode)

  const changeMode = useCallback((newMode: ViewMode) => {
    setMode(newMode)
    onModeChange?.(newMode)
  }, [onModeChange])

  return {
    mode,
    setMode: changeMode,
    isActive: mode === 'active',
    isHistory: mode === 'history',
    isAll: mode === 'all',
    isCharts: mode === 'charts',
  }
}



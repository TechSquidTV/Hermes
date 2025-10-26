import { useState, useEffect, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { themes, isValidTheme } from '@/themes'
import type { UserPreferences } from '@/types/auth'

export type Theme = string  // Theme ID (e.g., 'hermes', 'nord', 'dracula')
export type Mode = 'light' | 'dark' | 'system'

interface UseThemeOptions {
  defaultTheme?: Theme
  defaultMode?: Mode
}

export function useTheme(options: UseThemeOptions = {}) {
  const { 
    defaultTheme: fallbackTheme = 'hermes', 
    defaultMode: fallbackMode = 'system' 
  } = options

  const { user, updatePreferences } = useAuth()
  const queryClient = useQueryClient()

  // Get theme and mode from user preferences, or use defaults
  const userTheme = user?.preferences?.theme
  const userMode = user?.preferences?.mode

  // Validate and use theme (fallback to default if invalid)
  const activeTheme = userTheme && isValidTheme(userTheme) ? userTheme : fallbackTheme
  const activeMode = userMode || fallbackMode

  // System theme detection
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'dark'
  })

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // Calculate effective mode (resolve 'system' to actual mode)
  const effectiveMode = activeMode === 'system' ? systemTheme : activeMode

  // Apply theme to document
  useEffect(() => {
    if (typeof document === 'undefined') return

    const root = document.documentElement

    // Remove all theme classes and mode classes
    const classesToRemove: string[] = []
    root.classList.forEach((className) => {
      if (className.startsWith('theme-') || className === 'light' || className === 'dark') {
        classesToRemove.push(className)
      }
    })
    classesToRemove.forEach((className) => root.classList.remove(className))

    // Add theme class and mode class
    root.classList.add(`theme-${activeTheme}`)
    root.classList.add(effectiveMode)

    console.log(`[useTheme] Applied theme: theme-${activeTheme} ${effectiveMode}`, {
      activeTheme,
      activeMode,
      effectiveMode,
      systemTheme,
      userMode,
    })
  }, [activeTheme, effectiveMode, activeMode, systemTheme, userMode])

  // Mutation to update theme preferences
  const updateThemeMutation = useMutation({
    mutationFn: async (preferences: Partial<UserPreferences>) => {
      // Optimistically update preferences
      await updatePreferences(preferences)
    },
    onSuccess: () => {
      // Invalidate user queries to ensure fresh data
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
    onError: (error) => {
      console.error('[useTheme] Failed to update theme:', error)
    },
  })

  // Set theme (theme ID only)
  const setTheme = useCallback((newTheme: Theme) => {
    if (!isValidTheme(newTheme)) {
      console.warn(`[useTheme] Invalid theme: ${newTheme}`)
      return
    }

    updateThemeMutation.mutate({ theme: newTheme })
  }, [updateThemeMutation])

  // Set mode (light/dark/system)
  const setMode = useCallback((newMode: Mode) => {
    updateThemeMutation.mutate({ mode: newMode })
  }, [updateThemeMutation])

  // Set both theme and mode at once
  const setThemeAndMode = useCallback((newTheme: Theme, newMode: Mode) => {
    if (!isValidTheme(newTheme)) {
      console.warn(`[useTheme] Invalid theme: ${newTheme}`)
      return
    }

    updateThemeMutation.mutate({ theme: newTheme, mode: newMode })
  }, [updateThemeMutation])

  // Toggle mode (light → dark → system → light)
  const toggleMode = useCallback(() => {
    const nextMode: Mode = 
      activeMode === 'light' ? 'dark' :
      activeMode === 'dark' ? 'system' :
      'light'

    setMode(nextMode)
  }, [activeMode, setMode])

  return {
    // Current state
    theme: activeTheme,
    mode: activeMode,
    effectiveMode,
    systemTheme,

    // Setters
    setTheme,
    setMode,
    setThemeAndMode,
    toggleMode,

    // Status
    isLoading: updateThemeMutation.isPending,
    isLight: effectiveMode === 'light',
    isDark: effectiveMode === 'dark',
    isSystem: activeMode === 'system',

    // Available themes
    availableThemes: themes,
  }
}

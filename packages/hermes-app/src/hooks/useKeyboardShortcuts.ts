import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  handler: (event?: KeyboardEvent) => void
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const navigate = useNavigate()

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement ||
        event.target instanceof HTMLDivElement && event.target.contentEditable === 'true'
      ) {
        return
      }

      // Handle navigation shortcuts internally
      if (event.altKey && !event.ctrlKey && !event.shiftKey && !event.metaKey) {
        switch (event.key) {
          case '1':
            event.preventDefault()
            navigate({ to: '/' })
            return
          case '2':
            event.preventDefault()
            navigate({ to: '/queue' })
            return
          case '3':
            event.preventDefault()
            navigate({ to: '/settings' })
            return
        }
      }

      shortcuts.forEach(shortcut => {
        const matchesKey = event.key === shortcut.key
        const matchesCtrl = !!shortcut.ctrlKey === event.ctrlKey
        const matchesShift = !!shortcut.shiftKey === event.shiftKey
        const matchesAlt = !!shortcut.altKey === event.altKey
        const matchesMeta = !!shortcut.metaKey === event.metaKey

        if (matchesKey && matchesCtrl && matchesShift && matchesAlt && matchesMeta) {
          event.preventDefault()
          shortcut.handler(event)
        }
      })
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [shortcuts, navigate])
}

// Predefined shortcuts for common actions (navigation shortcuts are now handled internally in the hook)

export const globalShortcuts = [
  {
    key: 'k',
    ctrlKey: true,
    handler: () => {
      // Focus search input - we'll implement this when we add a global search
      const searchInput = document.querySelector('input[placeholder*="search" i], input[placeholder*="url" i]') as HTMLInputElement
      if (searchInput) {
        searchInput.focus()
        searchInput.select()
      }
    },
  },
  {
    key: 'n',
    ctrlKey: true,
    handler: () => {
      // Focus URL input on dashboard
      const urlInput = document.querySelector('input[placeholder*="url" i]') as HTMLInputElement
      if (urlInput) {
        urlInput.focus()
        urlInput.select()
      }
    },
  },
  {
    key: '/',
    handler: (event?: KeyboardEvent) => {
      // Focus search - prevent if already in input
      if (event?.target instanceof HTMLInputElement) return

      const searchInput = document.querySelector('input[placeholder*="search" i], input[placeholder*="url" i]') as HTMLInputElement
      if (searchInput) {
        event?.preventDefault()
        searchInput.focus()
        searchInput.select()
      }
    },
  },
  {
    key: 'Escape',
    handler: () => {
      // Clear focus or close modals
      if (document.activeElement instanceof HTMLInputElement) {
        (document.activeElement as HTMLInputElement).blur()
      }
    },
  },
]

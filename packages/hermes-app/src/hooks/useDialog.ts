import { useState, useCallback } from 'react'

interface UseDialogOptions {
  initialOpen?: boolean
  onOpenChange?: (open: boolean) => void
}

export function useDialog(options: UseDialogOptions = {}) {
  const { initialOpen = false, onOpenChange } = options
  const [isOpen, setIsOpen] = useState(initialOpen)

  const open = useCallback(() => {
    setIsOpen(true)
    onOpenChange?.(true)
  }, [onOpenChange])

  const close = useCallback(() => {
    setIsOpen(false)
    onOpenChange?.(false)
  }, [onOpenChange])

  const toggle = useCallback(() => {
    const newState = !isOpen
    setIsOpen(newState)
    onOpenChange?.(newState)
  }, [isOpen, onOpenChange])

  return {
    isOpen,
    open,
    close,
    toggle,
    setIsOpen,
  }
}



import { useState, useCallback } from 'react'

interface ConfirmationOptions {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'destructive'
}

interface ConfirmationState extends ConfirmationOptions {
  isOpen: boolean
  onConfirm?: () => void
  onCancel?: () => void
}

export function useConfirmation() {
  const [state, setState] = useState<ConfirmationState>({
    isOpen: false,
    title: 'Are you sure?',
    description: 'This action cannot be undone.',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    variant: 'default',
  })

  const showConfirmation = useCallback((
    options: ConfirmationOptions & {
      onConfirm: () => void
      onCancel?: () => void
    }
  ) => {
    setState({
      ...options,
      isOpen: true,
    })
  }, [])

  const hideConfirmation = useCallback(() => {
    setState(prev => ({ ...prev, isOpen: false }))
  }, [])

  const confirm = useCallback(() => {
    state.onConfirm?.()
    hideConfirmation()
  }, [state, hideConfirmation])

  const cancel = useCallback(() => {
    state.onCancel?.()
    hideConfirmation()
  }, [state, hideConfirmation])

  return {
    ...state,
    showConfirmation,
    hideConfirmation,
    confirm,
    cancel,
  }
}

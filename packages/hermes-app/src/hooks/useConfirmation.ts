import { useCallback, useEffect, useRef, useState } from 'react'

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
  const pending = useRef<((confirmed: boolean) => void) | null>(null)
  useEffect(() => () => { pending.current?.(false) }, [])
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
    pending.current?.(false)
    pending.current = null
    setState(prev => ({ ...prev, isOpen: false }))
  }, [])

  const confirm = useCallback(() => {
    pending.current?.(true)
    pending.current = null
    state.onConfirm?.()
    hideConfirmation()
  }, [state, hideConfirmation])

  const cancel = useCallback(() => {
    state.onCancel?.()
    hideConfirmation()
  }, [state, hideConfirmation])

  const askConfirmation = useCallback((options: ConfirmationOptions): Promise<boolean> => {
    pending.current?.(false)
    return new Promise(resolve => {
      pending.current = resolve
      setState({ ...options, isOpen: true })
    })
  }, [])

  return {
    ...state,
    askConfirmation,
    showConfirmation,
    hideConfirmation,
    confirm,
    cancel,
  }
}

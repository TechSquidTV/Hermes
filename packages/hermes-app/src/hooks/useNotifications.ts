import { toast } from 'sonner'
import { useCallback } from 'react'

export type NotificationType = 'success' | 'error' | 'warning' | 'info'

interface NotificationOptions {
  duration?: number
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function useNotifications() {
  const notify = useCallback((
    type: NotificationType,
    message: string,
    options: NotificationOptions = {}
  ) => {
    const { duration = 4000, description, action } = options

    switch (type) {
      case 'success':
        return toast.success(message, {
          duration,
          description,
          action: action ? {
            label: action.label,
            onClick: action.onClick,
          } : undefined,
        })
      case 'error':
        return toast.error(message, {
          duration: duration || 6000,
          description,
          action: action ? {
            label: action.label,
            onClick: action.onClick,
          } : undefined,
        })
      case 'warning':
        return toast.warning(message, {
          duration,
          description,
          action: action ? {
            label: action.label,
            onClick: action.onClick,
          } : undefined,
        })
      case 'info':
        return toast.info(message, {
          duration,
          description,
          action: action ? {
            label: action.label,
            onClick: action.onClick,
          } : undefined,
        })
      default:
        return toast(message, { duration, description })
    }
  }, [])

  const success = useCallback((message: string, options?: NotificationOptions) => {
    return notify('success', message, options)
  }, [notify])

  const error = useCallback((message: string, options?: NotificationOptions) => {
    return notify('error', message, options)
  }, [notify])

  const warning = useCallback((message: string, options?: NotificationOptions) => {
    return notify('warning', message, options)
  }, [notify])

  const info = useCallback((message: string, options?: NotificationOptions) => {
    return notify('info', message, options)
  }, [notify])

  const promise = useCallback(<T>(
    promise: Promise<T>,
    options: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: Error) => string)
    }
  ) => {
    return toast.promise(promise, options)
  }, [])

  return {
    notify,
    success,
    error,
    warning,
    info,
    promise,
  }
}



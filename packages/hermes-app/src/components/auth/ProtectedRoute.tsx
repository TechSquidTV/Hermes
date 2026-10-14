import { useEffect } from 'react'
import { useLocation, useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2 } from 'lucide-react'
import { ErrorDisplay } from '@/components/ui/error-display'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAuth?: boolean
}

export function ProtectedRoute({ children, requireAuth = true }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, isValidating, validationError, retryValidation } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const isAuthRoute = location.pathname.startsWith('/auth')
  const shouldRedirectToLogin = requireAuth && !isAuthenticated && !isAuthRoute
  const shouldRedirectToDashboard = !requireAuth && isAuthenticated

  useEffect(() => {
    if (isLoading || isValidating || validationError) {
      return
    }

    if (shouldRedirectToLogin) {
      void navigate({
        to: '/auth/login',
        search: { redirect: location.pathname },
        replace: true,
      })
      return
    }

    if (shouldRedirectToDashboard) {
      void navigate({ to: '/', replace: true })
    }
  }, [
    isLoading,
    isValidating,
    validationError,
    location.pathname,
    navigate,
    shouldRedirectToDashboard,
    shouldRedirectToLogin,
  ])

  if (isLoading || isValidating) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (validationError) return <ErrorDisplay message="Unable to verify your session. Your credentials have been kept; try again when the connection is available." onRetry={retryValidation} />

  if (shouldRedirectToLogin || shouldRedirectToDashboard) {
    return null
  }

  return <>{children}</>
}

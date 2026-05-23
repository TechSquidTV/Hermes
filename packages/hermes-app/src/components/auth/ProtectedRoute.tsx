import { useEffect } from 'react'
import { useLocation, useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAuth?: boolean
}

export function ProtectedRoute({ children, requireAuth = true }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, isValidating } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const isAuthRoute = location.pathname.startsWith('/auth')
  const shouldRedirectToLogin = requireAuth && !isAuthenticated && !isAuthRoute
  const shouldRedirectToDashboard = !requireAuth && isAuthenticated

  useEffect(() => {
    if (isLoading || isValidating) {
      return
    }

    if (shouldRedirectToLogin) {
      navigate({
        to: '/auth/login',
        search: { redirect: location.pathname },
        replace: true,
      })
      return
    }

    if (shouldRedirectToDashboard) {
      navigate({ to: '/', replace: true })
    }
  }, [
    isLoading,
    isValidating,
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

  if (shouldRedirectToLogin || shouldRedirectToDashboard) {
    return null
  }

  return <>{children}</>
}

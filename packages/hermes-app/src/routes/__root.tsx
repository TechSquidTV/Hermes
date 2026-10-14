import { Outlet, createRootRoute, useLocation } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { AppLayout } from '@/components/layout/AppLayout'
import { globalShortcuts, useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { DownloadEventsProvider } from '@/contexts/DownloadEventsContext'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/hooks/useTheme'

function RootLayout() {
  // Enable global keyboard shortcuts
  useKeyboardShortcuts(globalShortcuts)

  const { isValidating, isAuthenticated } = useAuth()
  const location = useLocation()
  const isAuthRoute = location.pathname.startsWith('/auth')
  
  // Apply theme from user preferences (fetched from database)
  // This ensures the correct theme is applied on every page load
  useTheme()

  // Show loading screen while validating auth and loading theme preferences
  if (isValidating) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background text-foreground">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <DownloadEventsProvider enabled={isAuthenticated}>
      {isAuthRoute ? (
        <>
          <div className="grain-overlay"></div>
          <main className="flex min-h-screen items-center justify-center bg-background text-foreground">
            <Outlet />
          </main>
        </>
      ) : (
        <AppLayout>
          <Outlet />
        </AppLayout>
      )}
      </DownloadEventsProvider>
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools />
          <ReactQueryDevtools />
        </>
      )}
    </>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})

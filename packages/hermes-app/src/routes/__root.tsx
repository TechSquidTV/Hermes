import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { AppLayout } from '@/components/layout/AppLayout'
import { useKeyboardShortcuts, globalShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/hooks/useTheme'

function RootLayout() {
  // Enable global keyboard shortcuts
  useKeyboardShortcuts(globalShortcuts)

  const { isValidating } = useAuth()
  
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
      <AppLayout>
        <Outlet />
      </AppLayout>
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


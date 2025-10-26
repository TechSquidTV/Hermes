import { createFileRoute, Outlet } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

function SettingsLayout() {
  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <Outlet />
    </div>
  )
}

export const Route = createFileRoute('/settings')({
  component: () => (
    <ProtectedRoute>
      <SettingsLayout />
    </ProtectedRoute>
  ),
})



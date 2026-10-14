import { Navigate, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/settings/')({
  component: () => <Navigate to="/settings/general" replace />,
})


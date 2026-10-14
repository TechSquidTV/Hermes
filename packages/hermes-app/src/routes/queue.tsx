import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { validateQueueSearch } from '@/lib/queueSearch'
import { QueueView } from '@/components/queue/QueueView'

function QueuePage() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  return <QueueView search={search} onChange={patch => { void navigate({ search: previous => ({ ...previous, ...patch }), replace: true }) }} />
}

export const Route = createFileRoute('/queue')({
  validateSearch: validateQueueSearch,
  component: () => (
    <ProtectedRoute>
      <QueuePage />
    </ProtectedRoute>
  ),
})


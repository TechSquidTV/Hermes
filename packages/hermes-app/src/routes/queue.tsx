import { createFileRoute } from '@tanstack/react-router'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { QueueView } from '@/components/queue/QueueView'

function QueuePage() {
  return <QueueView />
}

export const Route = createFileRoute('/queue')({
  component: () => (
    <ProtectedRoute>
      <QueuePage />
    </ProtectedRoute>
  ),
})


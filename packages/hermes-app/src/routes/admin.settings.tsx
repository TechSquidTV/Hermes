import { createFileRoute } from '@tanstack/react-router'
import { AdminSettingsPage } from '@/components/admin/AdminSettingsPage'
import { requireAdmin } from '@/lib/requireAdmin'

export const Route = createFileRoute('/admin/settings')({
  beforeLoad: requireAdmin,
  component: AdminSettingsPage,
})


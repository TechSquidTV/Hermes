import { createFileRoute } from '@tanstack/react-router'
import { AdminUsersPage } from '@/components/admin/AdminUsersPage'
import { requireAdmin } from '@/lib/requireAdmin'

export const Route = createFileRoute('/admin/users')({
  beforeLoad: requireAdmin,
  component: AdminUsersPage,
})

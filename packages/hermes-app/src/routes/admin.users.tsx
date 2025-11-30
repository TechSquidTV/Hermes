import { createFileRoute, redirect } from '@tanstack/react-router'
import { AdminUsersPage } from '@/components/admin/AdminUsersPage'
import { authService } from '@/services/auth'

export const Route = createFileRoute('/admin/users')({
  beforeLoad: async () => {
    try {
      const user = await authService.getCurrentUser()
      if (!user.isAdmin) {
        throw redirect({
          to: '/',
        })
      }
    } catch {
      throw redirect({
        to: '/auth/login',
      })
    }
  },
  component: AdminUsersPage,
})

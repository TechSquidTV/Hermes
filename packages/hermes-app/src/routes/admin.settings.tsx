import { createFileRoute, redirect } from '@tanstack/react-router'
import { AdminSettingsPage } from '@/components/admin/AdminSettingsPage'
import { authService } from '@/services/auth'

export const Route = createFileRoute('/admin/settings')({
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
  component: AdminSettingsPage,
})


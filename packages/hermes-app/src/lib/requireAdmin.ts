import { redirect } from '@tanstack/react-router'
import { authService } from '@/services/auth'
import { isAuthenticationError } from '@/services/http'

export async function requireAdmin(): Promise<void> {
  let user
  try {
    user = await authService.getCurrentUser()
  } catch (error) {
    if (isAuthenticationError(error)) throw redirect({ to: '/auth/login' })
    throw error
  }
  if (!user.isAdmin) throw redirect({ to: '/' })
}

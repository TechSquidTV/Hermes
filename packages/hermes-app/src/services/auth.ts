import type { AuthResponse, LoginCredentials, SignupCredentials, User } from '@/types/auth'
import { TokenStorage } from '@/utils/tokenStorage'
import { apiClient } from './api/client'
import { refreshSession } from './session'

class AuthService {
  private action = 0

  getBaseURL(): string {
    return apiClient.getBaseURL()
  }

  private async authenticate(
    endpoint: string,
    credentials: LoginCredentials | SignupCredentials
  ): Promise<AuthResponse> {
    const action = ++this.action
    const response = await apiClient.request<AuthResponse>(endpoint, {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify(credentials),
    })
    if (action !== this.action) throw new DOMException('Authentication changed', 'AbortError')
    TokenStorage.setTokens(response)
    return response
  }

  login(credentials: LoginCredentials): Promise<AuthResponse> {
    return this.authenticate('/auth/login', credentials)
  }
  signup(credentials: SignupCredentials): Promise<AuthResponse> {
    return this.authenticate('/auth/signup', credentials)
  }

  async logout(): Promise<void> {
    const action = ++this.action
    const version = TokenStorage.getVersion()
    try {
      await apiClient.request('/auth/logout', { method: 'POST' })
    } finally {
      if (action === this.action && version === TokenStorage.getVersion())
        TokenStorage.clearTokens()
    }
  }

  refreshToken(): ReturnType<typeof refreshSession> {
    return refreshSession()
  }

  getCurrentUser(signal?: AbortSignal): Promise<User> {
    return apiClient.request<User>('/auth/me', { signal })
  }

  updateProfile(updates: Pick<Partial<User>, 'email' | 'avatar' | 'preferences'>): Promise<User> {
    return apiClient.request<User>('/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiClient.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ currentPassword, newPassword }),
    })
  }
}

export const authService = new AuthService()

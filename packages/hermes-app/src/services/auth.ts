// Authentication Service

import type { User, LoginCredentials, SignupCredentials, AuthResponse } from '@/types/auth'
import { TokenStorage } from '@/utils/tokenStorage'
import { getApiBaseUrl } from '@/lib/config'

class AuthService {
  private baseURL: string

  constructor() {
    this.baseURL = getApiBaseUrl()
    console.log(`[AuthService] Using API base URL: ${this.baseURL}`)
  }

  public getBaseURL(): string {
    return this.baseURL
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    }

    // Add auth token if available using TokenStorage
    const token = TokenStorage.getAccessToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      // Handle authentication errors
      if (response.status === 401) {
        const errorData = await response.json().catch(() => ({ detail: 'Unauthorized' }))
        throw new Error(`401: ${errorData.detail || 'Unauthorized'}`)
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`)
      }

      return response.json()
    } catch (error) {
      console.error(`[AuthService] Request failed for ${endpoint}:`, error)
      throw error
    }
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })

    // Store tokens securely
    TokenStorage.setAccessToken(response.accessToken, 15) // 15 minutes expiry
    TokenStorage.setRefreshToken(response.refreshToken)

    return response
  }

  async signup(credentials: SignupCredentials): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })

    // Store tokens securely
    TokenStorage.setAccessToken(response.accessToken, 15) // 15 minutes expiry
    TokenStorage.setRefreshToken(response.refreshToken)

    return response
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('/auth/logout', {
        method: 'POST',
      })
    } catch (error) {
      console.warn('[AuthService] Logout API call failed:', error)
      // Continue with local cleanup even if API call fails
    }

    // Clear tokens from secure storage
    TokenStorage.clearTokens()
  }

  async refreshToken(): Promise<AuthResponse> {
    const refreshToken = TokenStorage.getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await this.request<AuthResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken }),
    })

    // Store new tokens securely
    TokenStorage.setAccessToken(response.accessToken, 15) // 15 minutes expiry
    TokenStorage.setRefreshToken(response.refreshToken)

    return response
  }

  async getCurrentUser(): Promise<User> {
    try {
      const headers = await this.getAuthHeaders()
      console.log('[AuthService] getCurrentUser - headers:', headers)
      console.log('[AuthService] getCurrentUser - URL:', `${this.baseURL}/auth/me`)
      
      const response = await fetch(`${this.baseURL}/auth/me`, {
        method: 'GET',
        headers,
      })

      console.log('[AuthService] getCurrentUser - response status:', response.status)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to get user data' }))
        console.error('[AuthService] getCurrentUser - error response:', errorData)
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const userData = await response.json()
      console.log('[AuthService] getCurrentUser - success:', userData.username)
      return userData
    } catch (error) {
      console.error('[AuthService] getCurrentUser failed:', error)
      throw error
    }
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const token = TokenStorage.getAccessToken()
    console.log('[AuthService] getAuthHeaders - token exists:', !!token, 'token length:', token?.length || 0)
    if (token) {
      console.log('[AuthService] getAuthHeaders - token preview:', token.substring(0, 20) + '...')
    }
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    return headers
  }


  async updateProfile(updates: Partial<User>): Promise<User> {
    return this.request<User>('/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.request<void>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ currentPassword, newPassword }),
    })
  }
}

export const authService = new AuthService()

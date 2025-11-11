// Admin Service for user management

import type { User } from '@/types/auth'
import { TokenStorage } from '@/utils/tokenStorage'
import { getApiBaseUrl } from '@/lib/config'

export interface CreateUserRequest {
  username: string
  email: string
  password: string
  isAdmin?: boolean
}

export interface UpdateAdminStatusRequest {
  isAdmin: boolean
}

export interface UpdateActiveStatusRequest {
  isActive: boolean
}

class AdminService {
  private baseURL: string

  constructor() {
    this.baseURL = getApiBaseUrl()
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    }

    // Add auth token
    const token = TokenStorage.getAccessToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      const errorData = await response.json().catch(() => ({ detail: 'Unauthorized' }))
      throw new Error(`401: ${errorData.detail || 'Unauthorized'}`)
    }

    if (response.status === 403) {
      const errorData = await response.json().catch(() => ({ error: { message: 'Forbidden' } }))
      const message = errorData.error?.message || errorData.detail || 'Forbidden'
      throw new Error(`403: ${message}`)
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Request failed' }))
      const message = errorData.error?.message || errorData.detail || response.statusText
      throw new Error(`HTTP ${response.status}: ${message}`)
    }

    return response.json()
  }

  async listUsers(): Promise<User[]> {
    return this.request<User[]>('/users/')
  }

  async createUser(data: CreateUserRequest): Promise<User> {
    return this.request<User>('/users/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateAdminStatus(userId: string, isAdmin: boolean): Promise<User> {
    return this.request<User>(`/users/${userId}/admin`, {
      method: 'PATCH',
      body: JSON.stringify({ isAdmin }),
    })
  }

  async updateActiveStatus(userId: string, isActive: boolean): Promise<User> {
    return this.request<User>(`/users/${userId}/active`, {
      method: 'PATCH',
      body: JSON.stringify({ isActive }),
    })
  }

  async deleteUser(userId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/users/${userId}`, {
      method: 'DELETE',
    })
  }
}

export const adminService = new AdminService()

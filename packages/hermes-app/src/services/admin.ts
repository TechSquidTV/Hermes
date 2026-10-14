// Admin Service for user management

import type { User } from '@/types/auth'
import { apiClient } from './api/client'

import type { components } from '@/types/api.generated'
export type CreateUserRequest = components['schemas']['UserCreateAdmin']

class AdminService {
  async listUsers(): Promise<User[]> {
    return apiClient.request<User[]>('/users/')
  }

  async createUser(data: CreateUserRequest): Promise<User> {
    return apiClient.request<User>('/users/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateAdminStatus(userId: string, isAdmin: boolean): Promise<User> {
    return apiClient.request<User>(`/users/${userId}/admin`, {
      method: 'PATCH',
      body: JSON.stringify({ isAdmin }),
    })
  }

  async updateActiveStatus(userId: string, isActive: boolean): Promise<User> {
    return apiClient.request<User>(`/users/${userId}/active`, {
      method: 'PATCH',
      body: JSON.stringify({ isActive }),
    })
  }

  async deleteUser(userId: string): Promise<{ message: string }> {
    return apiClient.request<{ message: string }>(`/users/${userId}`, {
      method: 'DELETE',
    })
  }
}

export const adminService = new AdminService()

// Authentication Types

import type { components } from '@/types/api.generated'

export type User = Omit<components['schemas']['UserResponse'], 'preferences'> & { preferences?: UserPreferences | null }

export interface UserPreferences {
  defaultFormat?: string
  defaultOutputDirectory?: string
  downloadSubtitles?: boolean
  downloadThumbnail?: boolean
  theme?: string  // Theme ID (e.g., 'hermes', 'nord', 'dracula')
  mode?: 'light' | 'dark' | 'system'  // Light/dark/system mode
  notifications?: boolean
}

export type LoginCredentials = components['schemas']['UserLogin']
export type SignupCredentials = components['schemas']['UserCreate']
export type AuthResponse = Omit<components['schemas']['AuthResponse'], 'user'> & { user: User }

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  isValidating: boolean
  validationError: Error | null
  retryValidation: () => void
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  signup: (credentials: SignupCredentials) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<void>
}
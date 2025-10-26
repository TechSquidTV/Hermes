// Authentication Types

export interface User {
  id: string
  username: string
  email: string
  avatar?: string
  createdAt: string
  preferences?: UserPreferences
}

export interface UserPreferences {
  defaultFormat?: string
  defaultOutputDirectory?: string
  downloadSubtitles?: boolean
  downloadThumbnail?: boolean
  theme?: string  // Theme ID (e.g., 'hermes', 'nord', 'dracula')
  mode?: 'light' | 'dark' | 'system'  // Light/dark/system mode
  notifications?: boolean
}

export interface LoginCredentials {
  username?: string
  email?: string
  password: string
}

export interface SignupCredentials {
  username: string
  email: string
  password: string
}

export interface AuthResponse {
  user: User
  accessToken: string
  refreshToken: string
}

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  isValidating: boolean
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  signup: (credentials: SignupCredentials) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<void>
}
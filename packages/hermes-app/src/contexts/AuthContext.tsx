// Authentication Context

import React, { createContext, useContext, useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth'
import { TokenStorage } from '@/utils/tokenStorage'
import type { User, AuthContextType, LoginCredentials, SignupCredentials, UserPreferences } from '@/types/auth'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isValidating, setIsValidating] = useState(true)
  const queryClient = useQueryClient()

  // Validate token with backend on mount
  useEffect(() => {
    const validateStoredToken = async () => {
      try {
        const token = TokenStorage.getAccessToken()
        if (token) {
          // Verify token with backend
          const userData = await authService.getCurrentUser()
          setUser(userData)
          console.log('[AuthContext] Token validated successfully:', userData.username)
        } else {
          console.log('[AuthContext] No token found, user not authenticated')
        }
      } catch (error) {
        console.error('[AuthContext] Token validation failed:', error)
        // Clear invalid tokens
        TokenStorage.clearTokens()
        setUser(null)

        // Attempt token refresh if 401 error
        if ((error as Error)?.message?.includes('401') || (error as Error)?.message?.includes('Unauthorized')) {
          try {
            await authService.refreshToken()
            // Retry validation with new token
            const userData = await authService.getCurrentUser()
            setUser(userData)
            console.log('[AuthContext] Token refreshed and validated successfully')
          } catch (refreshError) {
            console.error('[AuthContext] Token refresh failed:', refreshError)
          }
        }
      } finally {
        setIsValidating(false)
      }
    }

    validateStoredToken()
  }, [])  

  const loginMutation = useMutation({
    mutationFn: (credentials: LoginCredentials) => authService.login(credentials),
    onSuccess: (data) => {
      // Tokens are already stored in authService.login()
      setUser(data.user)
      setIsValidating(false) // Stop validation loading state
      console.log('[AuthContext] Login successful, user authenticated:', data.user.username)
      queryClient.invalidateQueries()
    },
    onError: (error: unknown) => {
      console.error('[AuthContext] Login failed:', error)
      // Clear any existing tokens on login failure
      TokenStorage.clearTokens()
      setUser(null)
      setIsValidating(false)
    }
  })

  const signupMutation = useMutation({
    mutationFn: (credentials: SignupCredentials) => authService.signup(credentials),
    onSuccess: (data) => {
      // Tokens are already stored in authService.signup()
      setUser(data.user)
      setIsValidating(false) // Stop validation loading state
      console.log('[AuthContext] Signup successful, user authenticated:', data.user.username)
      queryClient.invalidateQueries()
    },
    onError: (error: unknown) => {
      console.error('[AuthContext] Signup failed:', error)
      // Clear any existing tokens on signup failure
      TokenStorage.clearTokens()
      setUser(null)
      setIsValidating(false)
    }
  })

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await authService.logout()
    },
    onSuccess: () => {
      // Tokens are already cleared in authService.logout()
      setUser(null)
      setIsValidating(false)
      queryClient.clear()
      console.log('[AuthContext] Logout successful, tokens cleared')
    },
    onError: (error: unknown) => {
      console.error('[AuthContext] Logout failed:', error)
      // Still clear tokens even if API call fails
      TokenStorage.clearTokens()
      setUser(null)
      setIsValidating(false)
      queryClient.clear()
    }
  })

  const refreshTokenMutation = useMutation({
    mutationFn: () => authService.refreshToken(),
    onSuccess: () => {
      // Tokens are already stored in authService.refreshToken()
      console.log('[AuthContext] Token refresh successful')
    },
    onError: (error: unknown) => {
      console.error('[AuthContext] Token refresh failed:', error)
      // Clear tokens on refresh failure
      TokenStorage.clearTokens()
      setUser(null)
      setIsValidating(false)
    }
  })

  const updatePreferencesMutation = useMutation({
    mutationFn: async (preferences: Partial<UserPreferences>) => {
      if (!user) {
        throw new Error('User not authenticated')
      }

      // Update preferences via API
      const updatedUser = await authService.updateProfile({
        preferences: {
          ...user.preferences,
          ...preferences,
        },
      })

      return updatedUser
    },
    onMutate: async (newPreferences) => {
      // Optimistically update user preferences
      if (user) {
        setUser({
          ...user,
          preferences: {
            ...user.preferences,
            ...newPreferences,
          },
        })
      }
    },
    onSuccess: (updatedUser) => {
      // Update user state with server response
      setUser(updatedUser)
      console.log('[AuthContext] Preferences updated successfully')
    },
    onError: (error: unknown, _variables, _context) => {
      console.error('[AuthContext] Failed to update preferences:', error)
      // Revert optimistic update on error by refetching user
      authService.getCurrentUser().then(setUser).catch(console.error)
    },
  })

  const value: AuthContextType = {
    user,
    isLoading: loginMutation.isPending || signupMutation.isPending || logoutMutation.isPending,
    isValidating,
    isAuthenticated: !!user && !isValidating,
    login: async (credentials) => {
      await loginMutation.mutateAsync(credentials)
    },
    signup: async (credentials) => {
      await signupMutation.mutateAsync(credentials)
    },
    logout: logoutMutation.mutateAsync,
    refreshToken: async () => {
      await refreshTokenMutation.mutateAsync()
    },
    updatePreferences: async (preferences) => {
      await updatePreferencesMutation.mutateAsync(preferences)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

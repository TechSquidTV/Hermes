import React, { createContext, useContext, useRef, useState, useSyncExternalStore } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth'
import { isAuthenticationError } from '@/services/http'
import { TokenStorage } from '@/utils/tokenStorage'
import type {
  AuthContextType,
  LoginCredentials,
  SignupCredentials,
  User,
  UserPreferences,
} from '@/types/auth'

const AuthContext = createContext<AuthContextType | undefined>(undefined)
const USER_KEY = ['user'] as const
const userKey = (version = TokenStorage.getVersion()) => [...USER_KEY, version] as const

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const operation = useRef(0)
  const version = useSyncExternalStore(TokenStorage.subscribe, TokenStorage.getVersion)
  const hasCredentials = !!(TokenStorage.getAccessToken() || TokenStorage.getRefreshToken())
  const [suspendedVersion, setSuspendedVersion] = useState<number | null>(null)
  const enabled = suspendedVersion !== version
  const userQuery = useQuery({
    queryKey: userKey(version),
    enabled: enabled && hasCredentials,
    queryFn: async ({ signal }) => {
      const version = TokenStorage.getVersion()
      try {
        return await authService.getCurrentUser(signal)
      } catch (error) {
        if (isAuthenticationError(error) && version === TokenStorage.getVersion())
          TokenStorage.clearTokens()
        throw error
      }
    },
    retry: (count, error) => !isAuthenticationError(error) && count < 2,
    staleTime: 30_000,
  })
  const user = enabled && hasCredentials ? (userQuery.data ?? null) : null

  const begin = async () => {
    const id = ++operation.current
    await queryClient.cancelQueries({ queryKey: USER_KEY })
    return id
  }
  const authenticated = (data: { user: User }, id: number | undefined) => {
    if (id !== operation.current) return
    queryClient.clear()
    queryClient.setQueryData(userKey(), data.user)
    setSuspendedVersion(null)
  }
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginCredentials) => authService.login(credentials),
    onMutate: begin,
    onSuccess: (data, _variables, id) => authenticated(data, id),
  })
  const signupMutation = useMutation({
    mutationFn: (credentials: SignupCredentials) => authService.signup(credentials),
    onMutate: begin,
    onSuccess: (data, _variables, id) => authenticated(data, id),
  })
  const logoutMutation = useMutation({
    mutationFn: () => authService.logout(),
    onMutate: async () => {
      setSuspendedVersion(TokenStorage.getVersion())
      const id = await begin()
      queryClient.clear()
      return id
    },
    onSettled: (_data, _error, _variables, id) => {
      if (id === operation.current) {
        setSuspendedVersion(TokenStorage.getVersion())
        queryClient.clear()
      }
    },
  })
  const refreshMutation = useMutation({
    mutationFn: () => authService.refreshToken(),
    onMutate: () => TokenStorage.getVersion(),
    onError: (error, _variables, version) => {
      if (version === TokenStorage.getVersion() && isAuthenticationError(error)) {
        TokenStorage.clearTokens()
        setSuspendedVersion(TokenStorage.getVersion())
        queryClient.clear()
      }
    },
  })
  const preferencesMutation = useMutation({
    scope: { id: 'user-preferences' },
    mutationFn: async ({
      preferences,
      version,
      userId,
    }: {
      preferences: Partial<UserPreferences>
      version: number
      userId: string
    }) => {
      await queryClient.cancelQueries({ queryKey: USER_KEY })
      const current = queryClient.getQueryData<User>(userKey(version))
      if (!current || current.id !== userId || version !== TokenStorage.getVersion()) {
        throw new DOMException('Session changed', 'AbortError')
      }
      const updated = await authService.updateProfile({
        preferences: { ...current.preferences, ...preferences },
      })
      if (version === TokenStorage.getVersion()) queryClient.setQueryData(userKey(version), updated)
    },
  })

  const value: AuthContextType = {
    user,
    isLoading: loginMutation.isPending || signupMutation.isPending || logoutMutation.isPending,
    isValidating: enabled && hasCredentials && userQuery.isPending && userQuery.isFetching,
    validationError:
      enabled &&
      hasCredentials &&
      !user &&
      userQuery.error &&
      !isAuthenticationError(userQuery.error)
        ? userQuery.error
        : null,
    retryValidation: () => {
      void userQuery.refetch()
    },
    isAuthenticated: !!user,
    login: async (credentials) => {
      await loginMutation.mutateAsync(credentials)
    },
    signup: async (credentials) => {
      await signupMutation.mutateAsync(credentials)
    },
    logout: async () => {
      await logoutMutation.mutateAsync()
    },
    refreshToken: async () => {
      await refreshMutation.mutateAsync()
    },
    updatePreferences: async (preferences) => {
      await preferencesMutation.mutateAsync({
        preferences,
        version: TokenStorage.getVersion(),
        userId: user?.id ?? '',
      })
    },
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}

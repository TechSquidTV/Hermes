// API Client for Hermes Video Downloader

import type { components } from '@/types/api.generated'

type VideoInfo = components["schemas"]["VideoInfo"]

// Define types for API responses that aren't in the schema
interface HealthResponse {
  status: string
  timestamp: string
  version: string
  environment: string
}

interface DailyStats {
  date: string
  downloads: number
  success_rate: number
  total_size: number
}

interface TimelineSummary {
  total_downloads: number
  success_rate: number
  total_size: number
  avg_daily_downloads: number
  trend: string
  peak_day: string | null
  peak_downloads: number
  period: string
  days_count: number
}
type DownloadRequest = components["schemas"]["DownloadRequest"]
type DownloadResponse = components["schemas"]["DownloadResponse"]
type DownloadStatus = components["schemas"]["DownloadStatus"]
type CancelResponse = components["schemas"]["CancelResponse"]
type FormatInfo = components["schemas"]["FormatInfo"]
type Configuration = components["schemas"]["Configuration"]
type ConfigurationUpdate = components["schemas"]["ConfigurationUpdate"]
type BatchDownloadRequest = components["schemas"]["BatchDownloadRequest"]
type BatchDownloadResponse = components["schemas"]["BatchDownloadResponse"]
type DownloadQueue = components["schemas"]["DownloadQueue"]
type FileList = components["schemas"]["FileList"]
type DeleteFilesResponse = components["schemas"]["DeleteFilesResponse"]
type DownloadHistory = components["schemas"]["DownloadHistory"]
type StorageInfo = components["schemas"]["StorageInfo"]
type ApiStatistics = components["schemas"]["ApiStatistics"]
type CleanupRequest = components["schemas"]["CleanupRequest"]
type CleanupResponse = components["schemas"]["CleanupResponse"]
type ApiKeyCreate = components["schemas"]["ApiKeyCreate"]
type ApiKeyResponse = components["schemas"]["ApiKeyResponse"]
type ApiKeyListResponse = components["schemas"]["ApiKeyListResponse"]
type TokenResponse = components["schemas"]["TokenResponse"]

// SSE Token types
interface CreateSSETokenRequest {
  scope: string
  ttl?: number
}

interface SSETokenResponse {
  token: string
  expires_at: string
  scope: string
  permissions: string[]
  ttl: number
}

import { TokenStorage } from '@/utils/tokenStorage'
import { getApiBaseUrl } from '@/lib/config'

interface ApiRequestInit extends RequestInit {
  skipAuth?: boolean
}

class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = getApiBaseUrl()
    console.log(`[ApiClient] Using API base URL: ${this.baseURL}`)
  }

  public getBaseURL(): string {
    return this.baseURL
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const token = TokenStorage.getAccessToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    return headers
  }

  // Enhanced method for handling auth errors with better error messages
  private handleAuthError(error: unknown): Error {
    const errorMessage = error instanceof Error ? error.message : String(error)

    if (errorMessage.includes('401')) {
      return new Error('401: Authentication required')
    }

    if (errorMessage.includes('403')) {
      return new Error('403: Access denied')
    }

    if (errorMessage.includes('429')) {
      return new Error('429: Too many requests, please try again later')
    }

    return new Error(`Authentication error: ${errorMessage}`)
  }

  async request<T>(endpoint: string, options: ApiRequestInit = {}): Promise<T> {
    // Use endpoint as-is to match exact backend route definitions
    // FastAPI routes without trailing slashes should not receive them from the client
    const url = `${this.baseURL}${endpoint}`

    // Add auth headers unless skipAuth is true
    const skipAuth = options.skipAuth ?? false
    const { skipAuth: _, ...fetchOptions } = options

    if (!skipAuth) {
      const headers = await this.getAuthHeaders()
      fetchOptions.headers = {
        ...headers,
        ...fetchOptions.headers,
      }
    } else {
      fetchOptions.headers = {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      }
    }

    // Handle 401 errors by attempting token refresh
    const response = await fetch(url, fetchOptions)

    if (response.status === 401 && !skipAuth) {
      try {
        // Try to refresh token
        await this.refreshToken()

        // Retry request with new token
        const newHeaders = await this.getAuthHeaders()
        fetchOptions.headers = {
          ...newHeaders,
          ...fetchOptions.headers,
        }

        const retryResponse = await fetch(url, fetchOptions)
        if (!retryResponse.ok) {
          throw new Error(`HTTP ${retryResponse.status}: ${retryResponse.statusText}`)
        }

        return retryResponse.json()
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        window.location.href = '/auth/login'
        throw this.handleAuthError(refreshError)
      }
    }

    if (!response.ok) {
      throw this.handleAuthError(new Error(`HTTP ${response.status}: ${response.statusText}`))
    }

    return response.json()
  }

  // Health check - Use trailing slash to match API router
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health/')
  }

  // Video information
  async getVideoInfo(url: string, includeFormats = true): Promise<VideoInfo> {
    const params = new URLSearchParams({ url, include_formats: includeFormats.toString() })
    return this.request<VideoInfo>(`/info/?${params}`)
  }

  // Download management
  async startDownload(request: DownloadRequest): Promise<DownloadResponse> {
    return this.request<DownloadResponse>('/download', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getDownloadStatus(downloadId: string): Promise<DownloadStatus> {
    return this.request<DownloadStatus>(`/download/${downloadId}`)
  }

  async cancelDownload(downloadId: string): Promise<CancelResponse> {
    return this.request<CancelResponse>(`/download/${downloadId}/cancel`, {
      method: 'POST',
    })
  }

  async startBatchDownload(request: BatchDownloadRequest): Promise<BatchDownloadResponse> {
    // Remove trailing slash to match FastAPI route definition
    return this.request<BatchDownloadResponse>('/download/batch', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getDownloadQueue(status?: string, limit = 20, offset = 0): Promise<DownloadQueue> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    if (status && status !== 'all') {
      params.append('status', status)
    }
    return this.request<DownloadQueue>(`/queue/?${params}`)
  }

  // File management
  async getDownloadedFiles(params?: {
    directory?: string
    extension?: string
    min_size?: number
    max_size?: number
    created_after?: string
    created_before?: string
    limit?: number
    offset?: number
  }): Promise<FileList> {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString())
        }
      })
    }
    return this.request<FileList>(`/files/?${searchParams}`)
  }

  // History and statistics
  async getDownloadHistory(params?: {
    start_date?: string
    end_date?: string
    extractor?: string
    status?: string
    limit?: number
    offset?: number
  }): Promise<DownloadHistory> {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString())
        }
      })
    }
    return this.request<DownloadHistory>(`/history/?${searchParams}`)
  }

  async getApiStats(period: 'day' | 'week' | 'month' | 'year' = 'week'): Promise<ApiStatistics> {
    return this.request<ApiStatistics>(`/stats/?period=${period}`)
  }

  // Timeline and analytics endpoints
  async getTimelineStats(
    period: 'day' | 'week' | 'month' | 'year' = 'week',
    params?: {
      start_date?: string
      end_date?: string
      extractor?: string
      status?: string
    }
  ): Promise<DailyStats[]> {
    const searchParams = new URLSearchParams({ period })
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString())
        }
      })
    }
    return this.request<DailyStats[]>(`/timeline/?${searchParams}`)
  }

  async getTimelineSummary(
    period: 'day' | 'week' | 'month' | 'year' = 'week',
    params?: {
      start_date?: string
      end_date?: string
    }
  ): Promise<TimelineSummary> {
    const searchParams = new URLSearchParams({ period })
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString())
        }
      })
    }
    return this.request<TimelineSummary>(`/timeline/summary?${searchParams}`)
  }

  // Storage management
  async getStorageInfo(): Promise<StorageInfo> {
    return this.request<StorageInfo>('/storage')
  }

  async cleanupDownloads(request: CleanupRequest): Promise<CleanupResponse> {
    return this.request<CleanupResponse>('/cleanup', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // Formats
  async getAvailableFormats(): Promise<FormatInfo> {
    return this.request<FormatInfo>('/formats')
  }

  // Configuration
  async getPublicConfig(): Promise<{ allowPublicSignup: boolean }> {
    return this.request<{ allowPublicSignup: boolean }>('/config/public', {
      skipAuth: true,
    })
  }

  // Admin-only configuration (moved from /config to /admin/config)
  async getAdminConfig(): Promise<Configuration> {
    return this.request<Configuration>('/admin/config')
  }

  async updateAdminConfig(config: ConfigurationUpdate): Promise<Configuration> {
    return this.request<Configuration>('/admin/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  // Legacy method - deprecated, use getAdminConfig() instead
  async getConfiguration(): Promise<Configuration> {
    return this.getAdminConfig()
  }

  async updateConfiguration(config: ConfigurationUpdate): Promise<Configuration> {
    return this.updateAdminConfig(config)
  }

  // Admin Settings
  async getAdminSettings(): Promise<{
    allowPublicSignup: boolean
    updatedAt?: string
    updatedByUserId?: string
  }> {
    return this.request('/admin/settings')
  }

  async updateSignupSetting(enabled: boolean): Promise<{
    allowPublicSignup: boolean
    updatedAt?: string
    updatedByUserId?: string
  }> {
    return this.request('/admin/settings/signup', {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    })
  }

  // API Key Management
  async createApiKey(apiKeyData: ApiKeyCreate): Promise<ApiKeyResponse> {
    return this.request<ApiKeyResponse>('/auth/api-keys', {
      method: 'POST',
      body: JSON.stringify(apiKeyData),
    })
  }

  async getApiKeys(): Promise<ApiKeyListResponse[]> {
    return this.request<ApiKeyListResponse[]>('/auth/api-keys')
  }

  async revokeApiKey(apiKeyId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/auth/api-keys/${apiKeyId}`, {
      method: 'DELETE',
    })
  }

  // Private method for token refresh
  private async refreshToken(): Promise<TokenResponse> {
    const refreshToken = TokenStorage.getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await fetch(`${this.baseURL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Token refresh failed' }))
      throw new Error(`Token refresh failed: ${errorData.detail || response.statusText}`)
    }

    return response.json()
  }

  // Delete downloaded files
  async deleteFiles(filePaths: string[]): Promise<DeleteFilesResponse> {
    return this.request<DeleteFilesResponse>('/files', {
      method: 'DELETE',
      body: JSON.stringify({
        files: filePaths,
        confirm: true
      }),
    })
  }

  /**
   * Create ephemeral SSE token for secure, scoped SSE connections.
   *
   * SSE tokens solve the security issue of passing JWT tokens in query parameters
   * by providing short-lived, scoped, read-only tokens specifically for SSE.
   *
   * @param request - Token request with scope and optional TTL
   * @returns SSE token response with token, expiry, and permissions
   *
   * @example
   * ```typescript
   * // Get token for download progress
   * const { token } = await apiClient.createSSEToken({
   *   scope: `download:${downloadId}`,
   *   ttl: 600  // 10 minutes
   * });
   *
   * // Use token to connect to SSE
   * const eventSource = new EventSource(
   *   `/api/v1/events/downloads/${downloadId}?token=${token}`
   * );
   * ```
   */
  async createSSEToken(request: CreateSSETokenRequest): Promise<SSETokenResponse> {
    return this.request<SSETokenResponse>('/events/token', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // Get download file URL for direct download
  getDownloadFileUrl(filePath: string): string {
    // Construct the download URL with the file path as a query parameter
    return `${this.baseURL}/files/download?path=${encodeURIComponent(filePath)}`
  }
}

export const apiClient = new ApiClient()

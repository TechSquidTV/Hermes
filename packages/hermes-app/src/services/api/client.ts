// API Client for Hermes Video Downloader

import type { QueueRequestParams } from '@/types'
import type { components } from '@/types/api.generated'

type VideoInfo = components['schemas']['VideoInfo']
type HealthResponse = components['schemas']['HealthResponse']
type DailyStats = components['schemas']['DailyStats']
type TimelineSummary = components['schemas']['TimelineSummary']
type DownloadRequest = components['schemas']['DownloadRequest']
type DownloadResponse = components['schemas']['DownloadResponse']
type DownloadStatus = components['schemas']['DownloadStatus']
type CancelResponse = components['schemas']['CancelResponse']
type FormatInfo = components['schemas']['FormatInfo']
type Configuration = components['schemas']['Configuration']
type ConfigurationUpdate = components['schemas']['ConfigurationUpdate']
type BatchDownloadRequest = components['schemas']['BatchDownloadRequest']
type BatchDownloadResponse = components['schemas']['BatchDownloadResponse']
type DownloadQueue = components['schemas']['DownloadQueue']
type FileList = components['schemas']['FileList']
type DeleteFilesResponse = components['schemas']['DeleteFilesResponse']
type DownloadHistory = components['schemas']['DownloadHistory']
type StorageInfo = components['schemas']['StorageInfo']
type ApiStatistics = components['schemas']['ApiStatistics']
type CleanupRequest = components['schemas']['CleanupRequest']
type CleanupResponse = components['schemas']['CleanupResponse']
type ApiKeyCreate = components['schemas']['ApiKeyCreate']
type ApiKeyResponse = components['schemas']['ApiKeyResponse']
type ApiKeyListResponse = components['schemas']['ApiKeyListResponse']

type CreateSSETokenRequest = components['schemas']['CreateSSETokenRequest']
type SSETokenResponse = components['schemas']['SSETokenResponse']

import { TokenStorage } from '@/utils/tokenStorage'
import { getApiBaseUrl } from '@/lib/config'
import { refreshSession } from '../session'
import { checkResponse, isAuthenticationError, waitForSignal, withRequestSignal } from '../http'

interface ApiRequestInit extends RequestInit {
  skipAuth?: boolean
  timeoutMs?: number
}

type SearchParamValue = string | number | boolean | null | undefined
type SearchParams = Record<string, SearchParamValue>

function buildSearchParams(params?: SearchParams, initialParams?: SearchParams): URLSearchParams {
  const searchParams = new URLSearchParams()

  const appendParams = (values?: SearchParams) => {
    if (!values) return

    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value.toString())
      }
    })
  }

  appendParams(initialParams)
  appendParams(params)

  return searchParams
}

class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = getApiBaseUrl()
  }

  public getBaseURL(): string {
    return this.baseURL
  }

  private async send(
    endpoint: string,
    options: ApiRequestInit,
    signal: AbortSignal
  ): Promise<Response> {
    const { skipAuth = false, timeoutMs: _, ...init } = options
    const headers = new Headers(init.headers)
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
    const version = TokenStorage.getVersion()
    const renew = async () => {
      try {
        await waitForSignal(refreshSession(), signal)
      } catch (error) {
        if (isAuthenticationError(error) && version === TokenStorage.getVersion())
          TokenStorage.clearTokens()
        throw error
      }
    }
    if (!skipAuth && !TokenStorage.getAccessToken() && TokenStorage.getRefreshToken()) await renew()
    const token = skipAuth ? null : TokenStorage.getAccessToken()
    if (!skipAuth && token) headers.set('Authorization', `Bearer ${token}`)
    const url = `${this.baseURL}${endpoint}`
    const response = await fetch(url, { ...init, headers, signal })
    if (response.status !== 401 || skipAuth) return checkResponse(response)

    if (version !== TokenStorage.getVersion())
      throw new DOMException('Session changed', 'AbortError')
    const currentToken = TokenStorage.getAccessToken()
    if (!currentToken || headers.get('Authorization') === `Bearer ${currentToken}`) {
      await renew()
    }
    signal.throwIfAborted()
    const replacement = TokenStorage.getAccessToken()
    if (replacement) headers.set('Authorization', `Bearer ${replacement}`)
    else headers.delete('Authorization')
    const retried = await fetch(url, { ...init, headers, signal })
    if (retried.status === 401 && version === TokenStorage.getVersion()) TokenStorage.clearTokens()
    return checkResponse(retried)
  }

  async request<T>(endpoint: string, options: ApiRequestInit = {}): Promise<T> {
    return withRequestSignal(options.signal, options.timeoutMs ?? 30_000, async (signal) => {
      const response = await this.send(endpoint, options, signal)
      if (response.status === 204) return undefined as T
      return response.json()
    })
  }

  async downloadFile(filePath: string): Promise<Blob> {
    return withRequestSignal(undefined, 300_000, async (signal) => {
      const params = buildSearchParams({ path: filePath })
      const response = await this.send(`/files/download?${params}`, {}, signal)
      return response.blob()
    })
  }

  // Health check - Use trailing slash to match API router
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health/', { skipAuth: true })
  }

  // Video information
  async getVideoInfo(url: string, includeFormats = true, signal?: AbortSignal): Promise<VideoInfo> {
    const params = buildSearchParams({ url, include_formats: includeFormats })
    return this.request<VideoInfo>(`/info/?${params}`, { signal })
  }

  // Download management
  async startDownload(request: DownloadRequest): Promise<DownloadResponse> {
    return this.request<DownloadResponse>('/download/', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getDownloadStatus(downloadId: string, signal?: AbortSignal): Promise<DownloadStatus> {
    return this.request<DownloadStatus>(`/download/${downloadId}`, { signal })
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

  async getDownloadQueue(
    status?: string,
    limit = 20,
    offset = 0,
    filters: {
      viewMode?: QueueRequestParams['view_mode']
      search?: string
      sortBy?: QueueRequestParams['sort_by']
      sortOrder?: QueueRequestParams['sort_order']
    } = {},
    signal?: AbortSignal
  ): Promise<DownloadQueue> {
    const params = buildSearchParams({
      status: status === 'all' ? undefined : status,
      limit,
      offset,
      view_mode: filters.viewMode,
      search: filters.search,
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
    })
    return this.request<DownloadQueue>(`/queue/?${params}`, { signal })
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
    const searchParams = buildSearchParams(params)
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
    const searchParams = buildSearchParams(params)
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
    const searchParams = buildSearchParams(params, { period })
    return this.request<DailyStats[]>(`/timeline/?${searchParams}`)
  }

  async getTimelineSummary(
    period: 'day' | 'week' | 'month' | 'year' = 'week',
    params?: {
      start_date?: string
      end_date?: string
    }
  ): Promise<TimelineSummary> {
    const searchParams = buildSearchParams(params, { period })
    return this.request<TimelineSummary>(`/timeline/summary?${searchParams}`)
  }

  // Storage management
  async getStorageInfo(): Promise<StorageInfo> {
    return this.request<StorageInfo>('/storage/')
  }

  async cleanupDownloads(request: CleanupRequest): Promise<CleanupResponse> {
    return this.request<CleanupResponse>('/cleanup/', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // Formats
  async getAvailableFormats(): Promise<FormatInfo> {
    return this.request<FormatInfo>('/formats/')
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

  // Delete downloaded files
  async deleteFiles(filePaths: string[]): Promise<DeleteFilesResponse> {
    return this.request<DeleteFilesResponse>('/files/', {
      method: 'DELETE',
      body: JSON.stringify({
        files: filePaths,
        confirm: true,
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
  async createSSEToken(
    request: CreateSSETokenRequest,
    signal?: AbortSignal
  ): Promise<SSETokenResponse> {
    return this.request<SSETokenResponse>('/events/token', {
      signal,
      method: 'POST',
      body: JSON.stringify(request),
    })
  }
}

export const apiClient = new ApiClient()

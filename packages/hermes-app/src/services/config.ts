// Configuration Service

import { getApiBaseUrl } from '@/lib/config'

export interface PublicConfig {
  allowPublicSignup: boolean
}

interface PublicConfigResponse {
  allowPublicSignup?: boolean
  allow_public_signup?: boolean
}

class ConfigService {
  private baseURL: string

  constructor() {
    this.baseURL = getApiBaseUrl()
  }

  async getPublicConfig(): Promise<PublicConfig> {
    const url = `${this.baseURL}/config/public`

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(`HTTP ${response.status}: ${errorData.detail || response.statusText}`)
      }

      const data = await response.json() as PublicConfigResponse

      return {
        allowPublicSignup: data.allowPublicSignup ?? data.allow_public_signup ?? true,
      }
    } catch (error) {
      console.error('[ConfigService] Failed to fetch public config:', error)
      throw error
    }
  }
}

export const configService = new ConfigService()

/**
 * Runtime configuration utilities
 * 
 * Provides centralized access to runtime configuration that can be set
 * via Docker environment variables without rebuilding the application.
 */

/**
 * Get the API base URL from runtime config, build-time env, or default
 * 
 * Priority order:
 * 1. Runtime config (window.__RUNTIME_CONFIG__.API_BASE_URL) - Set via Docker env
 * 2. Build-time env (import.meta.env.VITE_API_BASE_URL) - Set during build
 * 3. Default (/api/v1) - Fallback for same-domain proxy setup
 * 
 * @returns The API base URL to use for all API requests
 * 
 * @example
 * ```ts
 * import { getApiBaseUrl } from '@/lib/config'
 * 
 * const apiUrl = getApiBaseUrl()
 * // Returns: "http://localhost:8001/api/v1" (in separate host setup)
 * // Returns: "/api/v1" (in single domain setup)
 * ```
 */
export function getApiBaseUrl(): string {
  return (
    window.__RUNTIME_CONFIG__?.API_BASE_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    '/api/v1'
  )
}

/**
 * Check if the app is running in development mode
 */
export function isDevelopment(): boolean {
  return import.meta.env.DEV
}

/**
 * Check if the app is running in production mode
 */
export function isProduction(): boolean {
  return import.meta.env.PROD
}

/**
 * Get the current environment name
 */
export function getEnvironment(): 'development' | 'production' {
  return import.meta.env.PROD ? 'production' : 'development'
}


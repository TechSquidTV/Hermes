/**
 * Global window type extensions for Hermes application
 */

/**
 * Runtime configuration injected by docker-entrypoint.sh
 * This allows runtime configuration of environment variables without rebuilding the Docker image
 */
interface RuntimeConfig {
  /** API base URL - can be configured at container startup */
  API_BASE_URL: string
}

declare global {
  interface Window {
    /** Runtime configuration loaded from /config.js */
    __RUNTIME_CONFIG__?: RuntimeConfig
  }
}

export {}

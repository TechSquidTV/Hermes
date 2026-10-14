/**
 * Debug logging utilities - only logs in development mode
 */

const isDev = import.meta.env.DEV

/**
 * Logging interface for development debugging
 * All logs are suppressed in production builds
 */
export const debug = {
  /**
   * Log informational messages (only in dev)
   */
  log: (...args: unknown[]) => {
    if (isDev) {
      console.log(...args)
    }
  },

  /**
   * Log warning messages (only in dev)
   */
  warn: (...args: unknown[]) => {
    if (isDev) {
      console.warn(...args)
    }
  },

  /**
   * Log error messages (only in dev)
   */
  error: (...args: unknown[]) => {
    if (isDev) {
      console.error(...args)
    }
  },

  /**
   * Log task tracking debug messages
   */
  taskTracking: (message: string, ...args: unknown[]) => {
    if (isDev) {
      console.log(`[TaskTracker] ${message}`, ...args)
    }
  }
}

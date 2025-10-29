/**
 * Custom error class for API errors with status code
 */
export class ApiError extends Error {
  public statusCode?: number
  public response?: Response

  constructor(message: string, statusCode?: number, response?: Response) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.response = response
  }
}

/**
 * Extract status code from error message or Error object
 * Handles various error formats from fetch, axios, and custom errors
 */
export function extractStatusCode(error: unknown): number | undefined {
  // Check if it's our custom ApiError
  if (error instanceof ApiError && error.statusCode) {
    return error.statusCode
  }

  // Check if it's a regular Error with a message
  if (error instanceof Error) {
    const message = error.message

    // Pattern 1: "401: Authentication required"
    const match401 = message.match(/^401[:\s]/i)
    if (match401) return 401

    const match403 = message.match(/^403[:\s]/i)
    if (match403) return 403

    const match429 = message.match(/^429[:\s]/i)
    if (match429) return 429

    // Pattern 2: "HTTP 500: Internal Server Error"
    const httpMatch = message.match(/HTTP\s+(\d{3})/i)
    if (httpMatch) {
      const code = parseInt(httpMatch[1], 10)
      if (!isNaN(code)) return code
    }

    // Pattern 3: Status code at start of message
    const startMatch = message.match(/^(\d{3})[:\s-]/i)
    if (startMatch) {
      const code = parseInt(startMatch[1], 10)
      if (!isNaN(code)) return code
    }
  }

  // Check if error object has statusCode property (axios, fetch, etc.)
  if (typeof error === 'object' && error !== null) {
    const errorObj = error as { statusCode?: number; status?: number }
    if (errorObj.statusCode) return errorObj.statusCode
    if (errorObj.status) return errorObj.status
  }

  return undefined
}

/**
 * Check if error is a network error (no response received)
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof Error) {
    const message = error.message.toLowerCase()
    return (
      message.includes('network') ||
      message.includes('failed to fetch') ||
      message.includes('networkerror') ||
      message.includes('fetch error')
    )
  }
  return false
}

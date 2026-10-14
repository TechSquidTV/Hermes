/**
 * Tests for error utilities
 *
 * Tests API error handling, status code extraction, and network error detection.
 */

import { describe, it, expect } from 'vitest'
import { ApiError, extractStatusCode, isNetworkError } from '../errors'

describe('ApiError', () => {
  it('retains an HTTP status and server detail', () => {
    const error = new ApiError(422, 'Invalid URL')
    expect(error).toBeInstanceOf(Error)
    expect(error.status).toBe(422)
    expect(error.message).toBe('HTTP 422: Invalid URL')
  })
})

describe('extractStatusCode', () => {
  describe('ApiError instances', () => {
    it('extracts status code from ApiError', () => {
      const error = new ApiError(404, 'Test')
      expect(extractStatusCode(error)).toBe(404)
    })

    it('returns undefined for ApiError without status code', () => {
      const error = new Error('Test')
      expect(extractStatusCode(error)).toBeUndefined()
    })
  })

  describe('Pattern 1: Status code at start', () => {
    it('extracts 401 from message starting with "401:"', () => {
      const error = new Error('401: Authentication required')
      expect(extractStatusCode(error)).toBe(401)
    })

    it('extracts 401 from message starting with "401 "', () => {
      const error = new Error('401 Unauthorized')
      expect(extractStatusCode(error)).toBe(401)
    })

    it('extracts 403 from message', () => {
      const error = new Error('403: Forbidden')
      expect(extractStatusCode(error)).toBe(403)
    })

    it('extracts 429 from message', () => {
      const error = new Error('429: Too Many Requests')
      expect(extractStatusCode(error)).toBe(429)
    })
  })

  describe('Pattern 2: HTTP prefix', () => {
    it('extracts status code from "HTTP 500" format', () => {
      const error = new Error('HTTP 500: Internal Server Error')
      expect(extractStatusCode(error)).toBe(500)
    })

    it('extracts status code from "HTTP 404" format', () => {
      const error = new Error('HTTP 404 Not Found')
      expect(extractStatusCode(error)).toBe(404)
    })

    it('handles case-insensitive HTTP prefix', () => {
      const error = new Error('http 503 Service Unavailable')
      expect(extractStatusCode(error)).toBe(503)
    })
  })

  describe('Pattern 3: Status code at start with various separators', () => {
    it('extracts status code with colon separator', () => {
      const error = new Error('500: Internal Error')
      expect(extractStatusCode(error)).toBe(500)
    })

    it('extracts status code with space separator', () => {
      const error = new Error('404 Not Found')
      expect(extractStatusCode(error)).toBe(404)
    })

    it('extracts status code with dash separator', () => {
      const error = new Error('503- Service Unavailable')
      expect(extractStatusCode(error)).toBe(503)
    })
  })

  describe('Status code from error object properties', () => {
    it('extracts from statusCode property', () => {
      const error = { statusCode: 400, message: 'Bad Request' }
      expect(extractStatusCode(error)).toBe(400)
    })

    it('extracts from status property', () => {
      const error = { status: 502, message: 'Bad Gateway' }
      expect(extractStatusCode(error)).toBe(502)
    })

    it('prefers statusCode over status', () => {
      const error = { statusCode: 404, status: 500 }
      expect(extractStatusCode(error)).toBe(404)
    })
  })

  describe('Edge cases', () => {
    it('returns undefined for error without status code', () => {
      const error = new Error('Generic error message')
      expect(extractStatusCode(error)).toBeUndefined()
    })

    it('returns undefined for non-error objects', () => {
      expect(extractStatusCode('string error')).toBeUndefined()
      expect(extractStatusCode(123)).toBeUndefined()
      expect(extractStatusCode(true)).toBeUndefined()
    })

    it('returns undefined for null', () => {
      expect(extractStatusCode(null)).toBeUndefined()
    })

    it('returns undefined for undefined', () => {
      expect(extractStatusCode(undefined)).toBeUndefined()
    })

    it('handles empty error message', () => {
      const error = new Error('')
      expect(extractStatusCode(error)).toBeUndefined()
    })

    it('handles status code in middle of message', () => {
      const error = new Error('Request failed with HTTP 404 error')
      expect(extractStatusCode(error)).toBe(404)
    })

    it('extracts status codes even if uncommon', () => {
      const error = new Error('999: Invalid code')
      expect(extractStatusCode(error)).toBe(999)
    })

    it('does not extract status code when not at start', () => {
      const error = new Error('Error 999 occurred')
      expect(extractStatusCode(error)).toBeUndefined()
    })

    it('handles multiple status codes, returns first match', () => {
      const error = new Error('401: Unauthorized, got 500')
      expect(extractStatusCode(error)).toBe(401)
    })
  })

  describe('Real-world error formats', () => {
    it('handles fetch API errors', () => {
      const error = new Error('401: Unauthorized')
      expect(extractStatusCode(error)).toBe(401)
    })

    it('handles axios-style errors', () => {
      const error = {
        message: 'Request failed',
        status: 403,
        statusCode: 403,
      }
      expect(extractStatusCode(error)).toBe(403)
    })

    it('handles custom API errors', () => {
      const error = new ApiError(401, 'Authentication failed')
      expect(extractStatusCode(error)).toBe(401)
    })
  })
})

describe('isNetworkError', () => {
  describe('Network error detection', () => {
    it('detects "network" in error message', () => {
      const error = new Error('Network error occurred')
      expect(isNetworkError(error)).toBe(true)
    })

    it('detects "failed to fetch" in error message', () => {
      const error = new Error('Failed to fetch')
      expect(isNetworkError(error)).toBe(true)
    })

    it('detects "networkerror" (one word) in error message', () => {
      const error = new Error('NetworkError: Connection refused')
      expect(isNetworkError(error)).toBe(true)
    })

    it('detects "fetch error" in error message', () => {
      const error = new Error('Fetch Error: Could not connect')
      expect(isNetworkError(error)).toBe(true)
    })

    it('is case-insensitive', () => {
      expect(isNetworkError(new Error('NETWORK ERROR'))).toBe(true)
      expect(isNetworkError(new Error('Failed To Fetch'))).toBe(true)
      expect(isNetworkError(new Error('NetworkError'))).toBe(true)
      expect(isNetworkError(new Error('FETCH ERROR'))).toBe(true)
    })
  })

  describe('Non-network errors', () => {
    it('returns false for API errors', () => {
      const error = new Error('401: Unauthorized')
      expect(isNetworkError(error)).toBe(false)
    })

    it('returns false for validation errors', () => {
      const error = new Error('Validation failed')
      expect(isNetworkError(error)).toBe(false)
    })

    it('returns false for server errors', () => {
      const error = new Error('500: Internal Server Error')
      expect(isNetworkError(error)).toBe(false)
    })

    it('returns false for generic errors', () => {
      const error = new Error('Something went wrong')
      expect(isNetworkError(error)).toBe(false)
    })
  })

  describe('Non-error inputs', () => {
    it('returns false for non-Error objects', () => {
      expect(isNetworkError('network error')).toBe(false)
      expect(isNetworkError({ message: 'network error' })).toBe(false)
      expect(isNetworkError(null)).toBe(false)
      expect(isNetworkError(undefined)).toBe(false)
      expect(isNetworkError(123)).toBe(false)
    })

    it('returns false for empty error message', () => {
      const error = new Error('')
      expect(isNetworkError(error)).toBe(false)
    })
  })

  describe('Real-world network errors', () => {
    it('detects fetch API network errors', () => {
      const error = new Error('Failed to fetch')
      expect(isNetworkError(error)).toBe(true)
    })

    it('detects connection timeout errors', () => {
      const error = new Error('Network request failed')
      expect(isNetworkError(error)).toBe(true)
    })

    it('detects browser network errors', () => {
      const error = new Error('NetworkError when attempting to fetch resource')
      expect(isNetworkError(error)).toBe(true)
    })
  })
})

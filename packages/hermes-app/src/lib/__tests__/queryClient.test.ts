/**
 * Tests for React Query client configuration
 */

import { describe, it, expect } from 'vitest'
import { queryClient } from '../queryClient'

describe('queryClient', () => {
  describe('Configuration', () => {
    it('is defined', () => {
      expect(queryClient).toBeDefined()
    })

    it('has default query options', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.queries).toBeDefined()
    })

    it('has default mutation options', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.mutations).toBeDefined()
    })
  })

  describe('Query Options', () => {
    it('has 5 minute staleTime', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.queries?.staleTime).toBe(5 * 60 * 1000)
    })

    it('has 10 minute gcTime', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.queries?.gcTime).toBe(10 * 60 * 1000)
    })

    it('has retry function', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.queries?.retry).toBeDefined()
      expect(typeof defaultOptions.queries?.retry).toBe('function')
    })
  })

  describe('Retry Logic', () => {
    const getRetryFunction = () => {
      const defaultOptions = queryClient.getDefaultOptions()
      return defaultOptions.queries?.retry as (
        failureCount: number,
        error: Error
      ) => boolean
    }

    it('does not retry on 400 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Bad Request'), { status: 400 })

      expect(retry(0, error)).toBe(false)
      expect(retry(1, error)).toBe(false)
      expect(retry(2, error)).toBe(false)
    })

    it('does not retry on 404 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Not Found'), { status: 404 })

      expect(retry(0, error)).toBe(false)
      expect(retry(1, error)).toBe(false)
    })

    it('does not retry on 401 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Unauthorized'), { status: 401 })

      expect(retry(0, error)).toBe(false)
    })

    it('does not retry on 403 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Forbidden'), { status: 403 })

      expect(retry(0, error)).toBe(false)
    })

    it('does not retry on 422 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Unprocessable Entity'), {
        status: 422,
      })

      expect(retry(0, error)).toBe(false)
    })

    it('retries on 500 errors up to 3 times', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Internal Server Error'), {
        status: 500,
      })

      expect(retry(0, error)).toBe(true)
      expect(retry(1, error)).toBe(true)
      expect(retry(2, error)).toBe(true)
      expect(retry(3, error)).toBe(false)
    })

    it('retries on 502 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Bad Gateway'), { status: 502 })

      expect(retry(0, error)).toBe(true)
      expect(retry(1, error)).toBe(true)
    })

    it('retries on 503 errors', () => {
      const retry = getRetryFunction()
      const error = Object.assign(new Error('Service Unavailable'), {
        status: 503,
      })

      expect(retry(0, error)).toBe(true)
      expect(retry(1, error)).toBe(true)
    })

    it('retries on network errors', () => {
      const retry = getRetryFunction()
      const error = new Error('Network error')

      expect(retry(0, error)).toBe(true)
      expect(retry(1, error)).toBe(true)
      expect(retry(2, error)).toBe(true)
    })

    it('stops retrying after 3 failures', () => {
      const retry = getRetryFunction()
      const error = new Error('Network error')

      expect(retry(3, error)).toBe(false)
      expect(retry(4, error)).toBe(false)
    })

    it('handles errors without status property', () => {
      const retry = getRetryFunction()
      const error = new Error('Generic error')

      expect(retry(0, error)).toBe(true)
      expect(retry(1, error)).toBe(true)
      expect(retry(2, error)).toBe(true)
      expect(retry(3, error)).toBe(false)
    })
  })

  describe('Mutation Options', () => {
    it('has retry set to 1', () => {
      const defaultOptions = queryClient.getDefaultOptions()
      expect(defaultOptions.mutations?.retry).toBe(1)
    })
  })
})

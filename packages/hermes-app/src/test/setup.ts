import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Suppress expected console warnings during tests
const originalConsoleLog = console.log
const originalConsoleWarn = console.warn
const originalConsoleError = console.error

// Control suppression via environment variable
const shouldSuppressLogs = process.env.VITEST_VERBOSE !== 'true'

// List of expected warning/error patterns that should be suppressed
const suppressedPatterns = [
  // TokenStorage errors
  '[TokenStorage] Error retrieving token:',
  '[TokenStorage] SessionStorage failed, falling back to localStorage:',
  '[TokenStorage] Failed to clear sessionStorage:',
  '[TokenStorage] Failed to clear localStorage:',
  // AuthService errors
  '[AuthService] Request failed',
  '[AuthService] getCurrentUser failed:',
  '[AuthService] getCurrentUser - error response:',
  '[AuthService] Logout API call failed:',
  'localStorage.getItem is not a function',
]

// List of debug log patterns that should be suppressed
const suppressedDebugPatterns = [
  // TokenStorage debug logs
  '[TokenStorage] Access token stored securely',
  '[TokenStorage] Refresh token stored',
  '[TokenStorage] All tokens cleared',
  '[TokenStorage] Token expired, cleared automatically',
  '[TokenStorage] getAccessToken',
  // ApiClient debug logs
  '[ApiClient] Using API base URL:',
  // AuthService debug logs
  '[AuthService] getAuthHeaders',
  '[AuthService] getCurrentUser - headers:',
  '[AuthService] getCurrentUser - URL:',
  '[AuthService] getCurrentUser - response status:',
  '[AuthService] getCurrentUser - success:',
]

console.log = (...args: unknown[]) => {
  if (!shouldSuppressLogs) {
    originalConsoleLog.apply(console, args)
    return
  }

  const message = args.join(' ')
  if (suppressedDebugPatterns.some((pattern) => message.includes(pattern))) {
    return
  }
  originalConsoleLog.apply(console, args)
}

console.warn = (...args: unknown[]) => {
  if (!shouldSuppressLogs) {
    originalConsoleWarn.apply(console, args)
    return
  }

  const message = args.join(' ')
  if (suppressedPatterns.some((pattern) => message.includes(pattern))) {
    return
  }
  originalConsoleWarn.apply(console, args)
}

console.error = (...args: unknown[]) => {
  if (!shouldSuppressLogs) {
    originalConsoleError.apply(console, args)
    return
  }

  const message = args.join(' ')
  if (suppressedPatterns.some((pattern) => message.includes(pattern))) {
    return
  }
  originalConsoleError.apply(console, args)
}


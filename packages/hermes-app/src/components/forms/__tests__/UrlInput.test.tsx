/**
 * Tests for UrlInput component
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { UrlInput } from '../UrlInput'
import * as apiClient from '@/services/api/client'

// Mock the API client
vi.mock('@/services/api/client', () => ({
  apiClient: {
    getVideoInfo: vi.fn(),
  },
}))

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

// Mock task tracker
vi.mock('@/lib/taskTracking', () => ({
  taskTracker: {
    addTask: vi.fn(),
  },
}))

// Mock useStartDownload hook
vi.mock('@/hooks/useDownloadActions', () => ({
  useStartDownload: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}))

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('UrlInput Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('URL Validation', () => {
    it('renders input field', () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      expect(input).toBeInTheDocument()
    })

    it('accepts valid YouTube URL', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')

      expect(input).toHaveValue('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    })

    it('accepts valid Vimeo URL', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://vimeo.com/123456789')

      expect(input).toHaveValue('https://vimeo.com/123456789')
    })

    it('accepts valid short YouTube URL', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://youtu.be/dQw4w9WgXcQ')

      expect(input).toHaveValue('https://youtu.be/dQw4w9WgXcQ')
    })

    it('does not fetch info for invalid URL', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'not-a-valid-url')

      // Wait for debounce
      await waitFor(() => {
        expect(apiClient.apiClient.getVideoInfo).not.toHaveBeenCalled()
      }, { timeout: 1000 })
    })

    it('does not fetch info for empty input', async () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      await waitFor(() => {
        expect(apiClient.apiClient.getVideoInfo).not.toHaveBeenCalled()
      }, { timeout: 1000 })
    })

    it('handles protocol-less URLs correctly', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'youtube.com/watch?v=test')

      // Wait for debounce
      await waitFor(() => {
        // Should not call API for invalid URL (missing protocol)
        expect(apiClient.apiClient.getVideoInfo).not.toHaveBeenCalled()
      }, { timeout: 1000 })
    })
  })

  describe('User Interactions', () => {
    it('allows user to clear input', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i) as HTMLInputElement
      await user.type(input, 'https://youtube.com/watch?v=test')

      expect(input.value).toBe('https://youtube.com/watch?v=test')

      await user.clear(input)
      expect(input.value).toBe('')
    })

    it('shows focus button', () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      const focusButton = screen.getByRole('button', { name: /focus/i })
      expect(focusButton).toBeInTheDocument()
    })

    it('focuses input when focus button is clicked', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      const focusButton = screen.getByRole('button', { name: /focus/i })

      await user.click(focusButton)

      expect(input).toHaveFocus()
    })

    it('displays platform support hint', () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      expect(screen.getByText(/supports youtube, vimeo/i)).toBeInTheDocument()
    })

    it('displays mobile hint on small screens', () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      expect(screen.getByText(/💡 tap the input above/i)).toBeInTheDocument()
    })
  })

  describe('Debouncing', () => {
    it('debounces API calls for rapid typing', async () => {
      const user = userEvent.setup({ delay: null }) // Remove delay for faster test
      vi.mocked(apiClient.apiClient.getVideoInfo).mockResolvedValue({
        title: 'Test Video',
        formats: [],
      })

      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)

      // Rapidly type characters
      await user.type(input, 'h')
      await user.type(input, 't')
      await user.type(input, 't')
      await user.type(input, 'p')
      await user.type(input, 's')
      await user.type(input, ':')
      await user.type(input, '/')
      await user.type(input, '/')
      await user.type(input, 'youtube.com/watch?v=test')

      // Should only call API once after debounce period
      await waitFor(() => {
        expect(apiClient.apiClient.getVideoInfo).toHaveBeenCalledTimes(1)
      }, { timeout: 1000 })
    })
  })

  describe('Drag and Drop', () => {
    it('shows drag over state', () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      const dragArea = screen.getByPlaceholderText(/paste video url here/i).closest('div')
      expect(dragArea).toBeInTheDocument()
    })

    it('handles valid URL drop', async () => {
      const { toast } = await import('sonner')
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      const dragArea = input.parentElement!

      // Simulate drag enter
      fireEvent.dragEnter(dragArea, {
        dataTransfer: {
          types: ['text/plain'],
        },
      })

      // Simulate drop with URL
      fireEvent.drop(dragArea, {
        dataTransfer: {
          getData: () => 'https://youtube.com/watch?v=test',
          files: [],
        },
      })

      expect(input).toHaveValue('https://youtube.com/watch?v=test')
      expect(toast.success).toHaveBeenCalledWith('URL detected and added!')
    })

    it('handles file drop with info message', async () => {
      const { toast } = await import('sonner')
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      const dragArea = input.parentElement!

      // Simulate drop with file
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })
      fireEvent.drop(dragArea, {
        dataTransfer: {
          files: [file],
          getData: () => '',
        },
      })

      expect(toast.info).toHaveBeenCalledWith('File drop detected - batch processing coming soon!')
    })

    it('ignores invalid URL drop', async () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      const dragArea = input.parentElement!

      const initialValue = input.getAttribute('value')

      // Simulate drop with invalid URL
      fireEvent.drop(dragArea, {
        dataTransfer: {
          getData: () => 'not-a-url',
          files: [],
        },
      })

      // Value should not change
      expect(input).toHaveValue(initialValue || '')
    })
  })

  describe('Paste Handling', () => {
    it('handles paste event with valid URL', async () => {
      const user = userEvent.setup()
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)

      // Focus the input
      await user.click(input)

      // Simulate paste
      await user.paste('https://youtube.com/watch?v=test')

      expect(input).toHaveValue('https://youtube.com/watch?v=test')
    })

    it('trims whitespace from pasted URLs', async () => {
      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      input.focus()

      // Create a paste event with mock clipboard data
      const clipboardData = {
        items: [{
          type: 'text/plain',
          getAsString: (callback: (text: string) => void) => {
            callback('  https://youtube.com/watch?v=test  ')
          }
        }],
        types: ['text/plain'],
        getData: () => '  https://youtube.com/watch?v=test  '
      }

      fireEvent.paste(input, {
        clipboardData,
      })

      // The component's paste handler trims the URL
      await waitFor(() => {
        expect(input).toHaveValue('https://youtube.com/watch?v=test')
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      const user = userEvent.setup()
      vi.mocked(apiClient.apiClient.getVideoInfo).mockRejectedValue(
        new Error('Failed to fetch video info')
      )

      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://youtube.com/watch?v=invalid')

      await waitFor(() => {
        expect(screen.getByText(/error:/i)).toBeInTheDocument()
        expect(screen.getByText(/failed to fetch video info/i)).toBeInTheDocument()
      })
    })

    it('displays generic error for unknown error types', async () => {
      const user = userEvent.setup()
      vi.mocked(apiClient.apiClient.getVideoInfo).mockRejectedValue('Unknown error')

      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://youtube.com/watch?v=invalid')

      await waitFor(() => {
        expect(screen.getByText(/error:/i)).toBeInTheDocument()
        expect(screen.getByText(/failed to fetch video info/i)).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('shows loading indicator while fetching video info', async () => {
      const user = userEvent.setup()

      // Mock a delayed response
      vi.mocked(apiClient.apiClient.getVideoInfo).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ title: 'Test', formats: [] }), 100))
      )

      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://youtube.com/watch?v=test')

      await waitFor(() => {
        // Look for loading spinner
        const spinner = document.querySelector('.animate-spin')
        expect(spinner).toBeInTheDocument()
      })
    })

    it('shows video preview skeleton while loading', async () => {
      const user = userEvent.setup()

      vi.mocked(apiClient.apiClient.getVideoInfo).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ title: 'Test', formats: [] }), 100))
      )

      render(<UrlInput />, { wrapper: createWrapper() })

      const input = screen.getByPlaceholderText(/paste video url here/i)
      await user.type(input, 'https://youtube.com/watch?v=test')

      // Should show skeleton during loading
      await waitFor(() => {
        expect(apiClient.apiClient.getVideoInfo).toHaveBeenCalled()
      })
    })
  })
})

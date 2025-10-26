/**
 * Tests for ApiKeySettings component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ApiKeySettings } from '../ApiKeySettings'

// Mock the useApiKeys hook
vi.mock('@/hooks/useApiKeys', () => ({
  useApiKeys: vi.fn(),
}))

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(),
  },
})

// Mock confirm
global.confirm = vi.fn()

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        data: [],
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const mockUseApiKeys = await import('@/hooks/useApiKeys').then(m => m.useApiKeys)

describe('ApiKeySettings', () => {
  const mockApiKeys = [
    {
      id: '1',
      name: 'Sonarr Integration',
      permissions: ['read', 'write'],
      rate_limit: 60,
      is_active: true,
      created_at: '2025-01-01T00:00:00Z',
      last_used: '2025-01-02T00:00:00Z',
      expires_at: null,
    },
    {
      id: '2',
      name: 'Mobile App',
      permissions: ['read'],
      rate_limit: 30,
      is_active: false,
      created_at: '2025-01-01T00:00:00Z',
      last_used: null,
      expires_at: null,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.confirm as any).mockReturnValue(true)
  })

  it('should render API keys list correctly', () => {
    mockUseApiKeys.mockReturnValue({
      keys: {
        data: mockApiKeys,
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    expect(screen.getByText('API Keys')).toBeInTheDocument()
    expect(screen.getByText(/Generate API keys for external applications/i)).toBeInTheDocument()
    expect(screen.getByText('Generate New Key')).toBeInTheDocument()

    // Check API keys are displayed
    expect(screen.getByText('Sonarr Integration')).toBeInTheDocument()
    expect(screen.getByText('Mobile App')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('should show loading state when fetching API keys', () => {
    mockUseApiKeys.mockReturnValue({
      keys: {
        data: undefined,
        isLoading: true,
        isSuccess: false,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: true,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    expect(screen.getByText('Loading API keys...')).toBeInTheDocument()
  })

  it('should show empty state when no API keys', () => {
    mockUseApiKeys.mockReturnValue({
      keys: {
        data: [],
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    expect(screen.getByText('No API keys generated yet')).toBeInTheDocument()
    expect(screen.getByText('Create your first API key to get started')).toBeInTheDocument()
  })

  it('should show create form when Generate New Key is clicked', async () => {
    const user = userEvent.setup()

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: [],
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    const generateButton = screen.getByText('Generate New Key')
    await user.click(generateButton)

    expect(screen.getByText('Create New API Key')).toBeInTheDocument()
    expect(screen.getByLabelText('Key Name')).toBeInTheDocument()
    expect(screen.getByText('Permissions')).toBeInTheDocument()
    expect(screen.getByText('read')).toBeInTheDocument()
    expect(screen.getByText('write')).toBeInTheDocument()
    expect(screen.getByText('download')).toBeInTheDocument()
    expect(screen.getByText('delete')).toBeInTheDocument()
  })

  it('should create API key when form is submitted', async () => {
    const user = userEvent.setup()
    const mockCreateKey = vi.fn().mockResolvedValue({
      id: '3',
      name: 'New Test Key',
      key: 'hm_1234567890abcdef',
      permissions: ['read'],
      rate_limit: 60,
      is_active: true,
      created_at: '2025-01-03T00:00:00Z',
      last_used: null,
      expires_at: null,
    })

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: [],
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: mockCreateKey,
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    // Open form
    await user.click(screen.getByText('Generate New Key'))

    // Fill form
    await user.type(screen.getByLabelText('Key Name'), 'New Test Key')
    await user.click(screen.getByText('read'))

    // Submit form
    await user.click(screen.getByText('Create Key'))

    expect(mockCreateKey).toHaveBeenCalledWith({
      name: 'New Test Key',
      permissions: ['read'],
    })
  })

  it.skip('should copy API key when copy button is clicked', async () => {
    const user = userEvent.setup()
    const mockClipboard = navigator.clipboard.writeText as any

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: mockApiKeys,
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    // Find copy buttons (there should be one for each API key)
    const copyButtons = screen.getAllByRole('button', { name: /copy/i })
    await user.click(copyButtons[0])

    expect(mockClipboard).toHaveBeenCalledWith('Key ID: 1')
  })

  it.skip('should revoke API key when revoke button is clicked', async () => {
    const user = userEvent.setup()
    const mockRevokeKey = vi.fn().mockResolvedValue({
      message: 'API key revoked successfully!',
    })

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: mockApiKeys,
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: mockRevokeKey,
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    // Find revoke buttons (trash icons)
    const revokeButtons = screen.getAllByRole('button', { name: /trash/i })
    await user.click(revokeButtons[0])

    // Confirm dialog should be called
    expect(global.confirm).toHaveBeenCalledWith(
      expect.stringContaining('revoke the API key "Sonarr Integration"')
    )

    // Since confirm returns true, revoke should be called
    expect(mockRevokeKey).toHaveBeenCalledWith('1')
  })

  it.skip('should not revoke API key when cancelled', async () => {
    const user = userEvent.setup()
    const mockRevokeKey = vi.fn()

    // Mock confirm to return false (cancelled)
    ;(global.confirm as any).mockReturnValue(false)

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: mockApiKeys,
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: mockRevokeKey,
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    const revokeButtons = screen.getAllByRole('button', { name: /trash/i })
    await user.click(revokeButtons[0])

    // Should not call revoke when cancelled
    expect(mockRevokeKey).not.toHaveBeenCalled()
  })

  it.skip('should toggle permissions in create form', async () => {
    const user = userEvent.setup()

    mockUseApiKeys.mockReturnValue({
      keys: {
        data: [],
        isLoading: false,
        isSuccess: true,
        isError: false,
      },
      createKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      revokeKey: {
        mutateAsync: vi.fn(),
        isPending: false,
      },
      isLoading: false,
    })

    render(<ApiKeySettings />, { wrapper: createWrapper() })

    // Open form
    await user.click(screen.getByText('Generate New Key'))

    // Initially no permissions selected
    expect(screen.getByText('read')).toBeInTheDocument()
    expect(screen.getByText('write')).toBeInTheDocument()

    // Toggle read permission
    await user.click(screen.getByText('read'))
    await user.click(screen.getByText('download'))

    // Submit form
    await user.click(screen.getByText('Create Key'))

    // Should include selected permissions
    expect((mockUseApiKeys as any)().createKey.mutateAsync).toHaveBeenCalledWith({
      name: '',
      permissions: ['read', 'download'],
    })
  })
})

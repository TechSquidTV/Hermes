import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiKeySettings } from '../ApiKeySettings'
import { apiClient } from '@/services/api/client'
import { TokenStorage } from '@/utils/tokenStorage'
import { toast } from 'sonner'

vi.mock('@/services/api/client')
vi.mock('@/utils/tokenStorage')
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

const keys: Awaited<ReturnType<typeof apiClient.getApiKeys>> = [
  { id: '1', name: 'Sonarr Integration', permissions: ['read', 'write'], rateLimit: 60,
    isActive: true, createdAt: '2025-01-01T00:00:00Z', lastUsed: null, expiresAt: null },
  { id: '2', name: 'Mobile App', permissions: ['read'], rateLimit: 30,
    isActive: false, createdAt: '2025-01-01T00:00:00Z', lastUsed: null, expiresAt: null },
]

function setup() {
  const user = userEvent.setup()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={queryClient}><ApiKeySettings /></QueryClientProvider>)
  return user
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(apiClient.getApiKeys).mockResolvedValue(keys)
  vi.mocked(apiClient.createApiKey).mockResolvedValue({ ...keys[0], name: 'New Key', key: 'hm_new_key' })
  vi.mocked(apiClient.revokeApiKey).mockResolvedValue({ message: 'Revoked' })
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  vi.mocked(TokenStorage.getAccessToken).mockReturnValue(null)
})

describe('ApiKeySettings', () => {
  it('renders active and inactive API keys', async () => {
    setup()
    expect(await screen.findByText('Sonarr Integration')).toBeInTheDocument()
    expect(screen.getByText('Mobile App')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('shows loading while fetching keys', () => {
    vi.mocked(apiClient.getApiKeys).mockImplementation(() => new Promise(() => {}))
    setup()
    expect(screen.getByText('Loading API keys...')).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    vi.mocked(apiClient.getApiKeys).mockResolvedValue([])
    setup()
    expect(await screen.findByText('No API keys generated yet')).toBeInTheDocument()
  })

  it('offers only permissions supported by the API', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    for (const name of ['read', 'write', 'download', 'admin']) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
    expect(screen.queryByRole('button', { name: 'delete' })).not.toBeInTheDocument()
  })

  it('cancels key creation', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Key Name')).not.toBeInTheDocument()
    expect(apiClient.createApiKey).not.toHaveBeenCalled()
  })

  it('rejects an empty key name', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    await user.click(screen.getByRole('button', { name: 'Create Key' }))
    expect(toast.error).toHaveBeenCalledWith('Please enter a name for the API key')
    expect(apiClient.createApiKey).not.toHaveBeenCalled()
  })

  it('creates a key and resets the form', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    await user.type(screen.getByLabelText('Key Name'), '  New Key  ')
    await user.click(screen.getByRole('button', { name: 'read' }))
    await user.click(screen.getByRole('button', { name: 'Create Key' }))
    await waitFor(() => expect(apiClient.createApiKey).toHaveBeenCalledWith({ name: 'New Key', permissions: ['read'] }))
    await waitFor(() => expect(screen.queryByLabelText('Key Name')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    expect(screen.getByLabelText('Key Name')).toHaveValue('')
  })

  it('toggles selected permissions before submission', async () => {
    const user = setup()
    await user.click(screen.getByRole('button', { name: 'Generate New Key' }))
    await user.type(screen.getByLabelText('Key Name'), 'New Key')
    await user.click(screen.getByRole('button', { name: 'read' }))
    await user.click(screen.getByRole('button', { name: 'write' }))
    await user.click(screen.getByRole('button', { name: 'read' }))
    await user.click(screen.getByRole('button', { name: 'download' }))
    await user.click(screen.getByRole('button', { name: 'Create Key' }))
    await waitFor(() => expect(apiClient.createApiKey).toHaveBeenCalledWith({ name: 'New Key', permissions: ['write', 'download'] }))
  })

  it('copies a key ID', async () => {
    const user = setup()
    const clipboard = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
    await user.click(await screen.findByRole('button', { name: 'Copy key ID for Sonarr Integration' }))
    expect(clipboard).toHaveBeenCalledWith('Key ID: 1')
  })

  it('revokes a key after confirmation', async () => {
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Revoke key Sonarr Integration' }))
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Sonarr Integration'))
    await waitFor(() => expect(apiClient.revokeApiKey).toHaveBeenCalledWith('1'))
  })

  it('does not revoke a key when confirmation is cancelled', async () => {
    vi.mocked(window.confirm).mockReturnValue(false)
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Revoke key Sonarr Integration' }))
    expect(apiClient.revokeApiKey).not.toHaveBeenCalled()
  })

  it('copies the JWT token', async () => {
    vi.mocked(TokenStorage.getAccessToken).mockReturnValue('test-token')
    const user = setup()
    const clipboard = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
    await user.click(screen.getByRole('button', { name: 'Copy JWT token' }))
    expect(clipboard).toHaveBeenCalledWith('test-token')
    expect(toast.success).toHaveBeenCalledWith('JWT token copied to clipboard!')
  })

  it('reports clipboard rejection without claiming success', async () => {
    vi.mocked(TokenStorage.getAccessToken).mockReturnValue('test-token')
    const user = setup()
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('Permission denied'))
    await user.click(screen.getByRole('button', { name: 'Copy JWT token' }))
    expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('Could not copy'))
    expect(toast.success).not.toHaveBeenCalled()
  })
})

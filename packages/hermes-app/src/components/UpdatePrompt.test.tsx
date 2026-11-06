import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { UpdatePrompt } from './UpdatePrompt'

const current = '11111111-1111-4111-8111-111111111111'
const next = '22222222-2222-4222-8222-222222222222'

describe('UpdatePrompt', () => {
  const request = vi.fn<typeof fetch>()

  beforeEach(() => {
    vi.stubEnv('DEV', false)
    vi.stubGlobal('__HERMES_BUILD_ID__', current)
    vi.stubGlobal('fetch', request)
    request.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('checks the deployed frontend without caching and stays quiet for the same build', async () => {
    request.mockResolvedValue(new Response(current))
    render(<UpdatePrompt />)
    await waitFor(() => expect(request).toHaveBeenCalledOnce())
    expect(request.mock.calls[0]?.[0]).toBe('/build-id.txt')
    expect(request.mock.calls[0]?.[1]?.cache).toBe('no-store')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('prompts on focus after a deployment and preserves the open page until reload is chosen', async () => {
    request.mockResolvedValueOnce(new Response(current))
    render(<UpdatePrompt />)
    await act(async () => {})
    request.mockResolvedValueOnce(new Response(next))
    fireEvent.focus(window)
    expect(await screen.findByRole('status')).toHaveTextContent('A new version of Hermes is ready.')
    expect(screen.getByRole('button', { name: 'Reload' })).toBeVisible()
    expect(screen.getByText(/Save any changes/)).toBeVisible()
  })

  it('ignores outages and SPA fallback responses, then retries successfully', async () => {
    request.mockRejectedValueOnce(new TypeError('offline'))
    render(<UpdatePrompt />)
    await act(async () => {})
    request.mockResolvedValueOnce(new Response('<html>old server</html>'))
    fireEvent.focus(window)
    await act(async () => {})
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    request.mockResolvedValueOnce(new Response(next))
    fireEvent.focus(window)
    expect(await screen.findByRole('status')).toBeVisible()
  })

  it('aborts in-flight checks and removes listeners when the page unmounts', async () => {
    request.mockReturnValue(new Promise<Response>(() => {}))
    const { unmount } = render(<UpdatePrompt />)
    const signal = request.mock.calls[0]?.[1]?.signal
    unmount()
    expect(signal?.aborted).toBe(true)
    fireEvent.focus(window)
    expect(request).toHaveBeenCalledOnce()
  })
})

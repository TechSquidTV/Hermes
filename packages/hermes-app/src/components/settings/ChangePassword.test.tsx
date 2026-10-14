import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from '@/services/auth'
import { ChangePassword } from './ChangePassword'

vi.mock('@/services/auth', () => ({ authService: { changePassword: vi.fn() } }))
beforeEach(() => vi.resetAllMocks())
async function setup(confirmation = 'NewPassword123') {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ChangePassword />
    </QueryClientProvider>
  )
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Change Password' }))
  await user.type(screen.getByLabelText('Current password'), 'OldPassword123')
  await user.type(screen.getByLabelText('New password', { exact: true }), 'NewPassword123')
  await user.type(screen.getByLabelText('Confirm new password'), confirmation)
  return user
}
describe('ChangePassword', () => {
  it('validates confirmation before sending a change', async () => {
    const user = await setup('DifferentPassword')
    await user.click(screen.getByRole('button', { name: 'Save password' }))
    expect(screen.getByText('Passwords must match')).toBeInTheDocument()
    expect(authService.changePassword).not.toHaveBeenCalled()
  })
  it('sends the entered passwords and clears the form after success', async () => {
    vi.mocked(authService.changePassword).mockResolvedValue()
    const user = await setup()
    await user.click(screen.getByRole('button', { name: 'Save password' }))
    expect(authService.changePassword).toHaveBeenCalledWith('OldPassword123', 'NewPassword123')
    await user.click(screen.getByRole('button', { name: 'Change Password' }))
    expect(screen.getByLabelText('Current password')).toHaveValue('')
    expect(screen.getByLabelText('New password', { exact: true })).toHaveValue('')
  })
  it('shows server errors and leaves the form available to correct', async () => {
    vi.mocked(authService.changePassword).mockRejectedValue(
      new Error('Current password is incorrect')
    )
    const user = await setup()
    await user.click(screen.getByRole('button', { name: 'Save password' }))
    expect(await screen.findByText('Current password is incorrect')).toBeInTheDocument()
    expect(authService.changePassword).toHaveBeenCalledOnce()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockRegister = vi.fn()

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: null,
      accessToken: null,
      isLoading: false,
      login: vi.fn(),
      register: mockRegister,
      logout: vi.fn(),
    }),
  }
})

import { RegisterPage } from '../pages/RegisterPage'

const renderPage = (invite?: string) =>
  render(
    <MemoryRouter initialEntries={[`/register${invite ? `?invite=${invite}` : ''}`]}>
      <RegisterPage />
    </MemoryRouter>
  )

beforeEach(() => {
  mockNavigate.mockReset()
  mockRegister.mockReset()
})

describe('RegisterPage', () => {
  it('shows_invite_code_field_without_url_param', () => {
    renderPage()
    expect(screen.getByLabelText(/invite code/i)).toBeInTheDocument()
  })

  it('hides_invite_code_field_when_url_param_present', () => {
    renderPage('abc123xyz')
    expect(screen.queryByLabelText(/invite code/i)).not.toBeInTheDocument()
  })

  it('submits_invite_code_from_url_param', async () => {
    mockRegister.mockResolvedValue(undefined)

    renderPage('abc123xyz')

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'friend@example.com')
    await user.type(screen.getByLabelText(/password/i), 'mypassword1')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockRegister).toHaveBeenCalledWith('friend@example.com', 'mypassword1', 'abc123xyz')
  })

  it('navigates_to_login_after_successful_registration', async () => {
    mockRegister.mockResolvedValue(undefined)

    renderPage('invite-code')

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'friend@example.com')
    await user.type(screen.getByLabelText(/password/i), 'mypassword1')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/login', { state: { registered: true } })
  })

  it('shows_error_when_invalid_invite_code', async () => {
    mockRegister.mockRejectedValue(new Error('Invalid invite code'))

    renderPage('bad-code')

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /email/i }), 'friend@example.com')
    await user.type(screen.getByLabelText(/password/i), 'mypassword1')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

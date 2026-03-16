import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockGoogleLogin = vi.fn()

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: null,
      accessToken: null,
      isLoading: false,
      googleLogin: mockGoogleLogin,
      logout: vi.fn(),
    }),
  }
})

import { LoginPage } from '../pages/LoginPage'

beforeEach(() => {
  mockNavigate.mockReset()
  mockGoogleLogin.mockReset()
})

describe('LoginPage', () => {
  it('renders_login_form', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.getByRole('textbox', { name: /google id token/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('submits_id_token', async () => {
    mockGoogleLogin.mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /google id token/i }), 'fake-id-token')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(mockGoogleLogin).toHaveBeenCalledWith('fake-id-token')
  })

  it('shows_error_on_failure', async () => {
    mockGoogleLogin.mockRejectedValue(new Error('Invalid credentials'))

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /google id token/i }), 'bad-token')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('navigates_to_calendar_on_success', async () => {
    mockGoogleLogin.mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: /google id token/i }), 'fake-id-token')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/calendar')
  })
})

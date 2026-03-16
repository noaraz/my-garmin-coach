import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
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
      isAdmin: false,
      googleLogin: mockGoogleLogin,
      logout: vi.fn(),
    }),
  }
})

// Mock GoogleLogin to render a button that triggers onSuccess with a fake credential
let capturedOnError: (() => void) | null = null

vi.mock('@react-oauth/google', () => ({
  GoogleLogin: (props: { onSuccess: (response: { credential?: string }) => void; onError?: () => void }) => {
    capturedOnError = props.onError ?? null
    return <button data-testid="google-login-btn" onClick={() => props.onSuccess({ credential: 'fake-google-credential' })}>Sign in with Google</button>
  },
}))

import { LoginPage } from '../pages/LoginPage'

beforeEach(() => {
  mockNavigate.mockReset()
  mockGoogleLogin.mockReset()
  capturedOnError = null
})

describe('LoginPage', () => {
  it('renders_sign_in_heading_and_google_button', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByTestId('google-login-btn')).toBeInTheDocument()
  })

  it('does_not_render_email_or_password_fields', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.queryByRole('textbox', { name: /email/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: /password/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: /google id token/i })).not.toBeInTheDocument()
  })

  it('calls_googleLogin_and_navigates_on_google_success', async () => {
    mockGoogleLogin.mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.click(screen.getByTestId('google-login-btn'))

    expect(mockGoogleLogin).toHaveBeenCalledWith('fake-google-credential')
    // Wait for navigate
    await vi.waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/calendar')
    })
  })

  it('shows_error_when_googleLogin_rejects', async () => {
    mockGoogleLogin.mockRejectedValue(new Error('Invalid credentials'))

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.click(screen.getByTestId('google-login-btn'))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('shows_error_when_google_onError_fires', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    // Simulate Google sign-in error
    act(() => {
      if (capturedOnError) {
        capturedOnError()
      }
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Google sign-in failed')
  })
})

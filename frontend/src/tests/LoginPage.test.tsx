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

vi.mock('@react-oauth/google', () => ({
  useGoogleOAuth: () => ({
    clientId: 'test-client-id',
    scriptLoadedSuccessfully: true,
  }),
  GoogleOAuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

import { LoginPage } from '../pages/LoginPage'

// Capture the GIS token client callback so tests can invoke it
type TokenCallback = (response: { access_token?: string; error?: string }) => void
let capturedTokenCallback: TokenCallback | null = null
let mockRequestAccessToken: ReturnType<typeof vi.fn>

beforeEach(() => {
  mockNavigate.mockReset()
  mockGoogleLogin.mockReset()
  capturedTokenCallback = null
  mockRequestAccessToken = vi.fn()

  // Mock the Google Identity Services initTokenClient global
  ;(window as unknown as Record<string, unknown>).google = {
    accounts: {
      oauth2: {
        initTokenClient: vi.fn((config: { callback: TokenCallback }) => {
          capturedTokenCallback = config.callback
          return { requestAccessToken: mockRequestAccessToken }
        }),
      },
    },
  }
})

describe('LoginPage', () => {
  it('renders_sign_in_heading_and_google_button', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in with google/i })).toBeInTheDocument()
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
    await user.click(screen.getByRole('button', { name: /sign in with google/i }))

    expect(mockRequestAccessToken).toHaveBeenCalled()

    // Simulate the GIS callback with a fake access token
    await act(async () => {
      capturedTokenCallback?.({ access_token: 'fake-access-token' })
    })

    expect(mockGoogleLogin).toHaveBeenCalledWith('fake-access-token')
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
    await user.click(screen.getByRole('button', { name: /sign in with google/i }))

    await act(async () => {
      capturedTokenCallback?.({ access_token: 'fake-access-token' })
    })

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('shows_error_when_google_onError_fires', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    )

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /sign in with google/i }))

    // Simulate GIS callback returning an error
    await act(async () => {
      capturedTokenCallback?.({ error: 'access_denied' })
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Google sign-in failed')
  })
})

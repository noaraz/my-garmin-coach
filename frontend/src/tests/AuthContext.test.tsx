import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '../contexts/AuthContext'

const { mockGoogleAuth, mockTryRefreshToken } = vi.hoisted(() => ({
  mockGoogleAuth: vi.fn().mockResolvedValue({
    access_token: 'header.eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.sig',
    token_type: 'bearer',
  }),
  mockTryRefreshToken: vi.fn().mockResolvedValue(false),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    googleAuth: mockGoogleAuth,
    tryRefreshToken: mockTryRefreshToken,
  }
})

// A valid JWT payload: { userId: 1, email: "test@example.com", exp: 9999999999 }
// base64url-encoded: eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0
const VALID_TOKEN =
  'header.eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.sig'

// Expired token payload: { userId: 1, email: "test@example.com", exp: 1000000000 } (year 2001)
// base64url-encoded: eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6MTAwMDAwMDAwMH0
const EXPIRED_TOKEN =
  'header.eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6MTAwMDAwMDAwMH0.sig'

function AuthConsumer() {
  const { user, isLoading, logout } = useAuth()
  if (isLoading) return <div>loading</div>
  if (!user) return <div>no user</div>
  return (
    <div>
      <span data-testid="email">{user.email}</span>
      <button onClick={async () => await logout()}>logout</button>
    </div>
  )
}

beforeEach(() => {
  localStorage.clear()
  mockGoogleAuth.mockReset()
  mockGoogleAuth.mockResolvedValue({
    access_token: VALID_TOKEN,
    token_type: 'bearer',
  })
  mockTryRefreshToken.mockReset()
  mockTryRefreshToken.mockResolvedValue(false)
})

describe('AuthContext', () => {
  it('renders_children_with_auth_context', () => {
    render(
      <AuthProvider>
        <div data-testid="child">hello</div>
      </AuthProvider>
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('googleLogin_stores_tokens_and_sets_user', async () => {
    function LoginTrigger() {
      const { googleLogin, user } = useAuth()
      return (
        <div>
          <button onClick={() => googleLogin('fake-id-token')}>login</button>
          {user && <span data-testid="email">{user.email}</span>}
        </div>
      )
    }

    render(
      <AuthProvider>
        <LoginTrigger />
      </AuthProvider>
    )

    const { userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'login' }))

    expect(localStorage.getItem('access_token')).toBe(VALID_TOKEN)
    expect(localStorage.getItem('refresh_token')).toBeNull() // refresh token is now httpOnly cookie only
    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')
  })

  it('logout_clears_tokens', async () => {
    localStorage.setItem('access_token', VALID_TOKEN)

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')

    const { userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'logout' }))

    expect(screen.getByText('no user')).toBeInTheDocument()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('initializes_from_localStorage_on_mount', async () => {
    localStorage.setItem('access_token', VALID_TOKEN)

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')
  })

  it('AuthContext_validToken_restoresSession', async () => {
    localStorage.setItem('access_token', VALID_TOKEN)

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    // Should restore session without calling tryRefreshToken
    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')
    expect(mockTryRefreshToken).not.toHaveBeenCalled()
  })

  it('AuthContext_noStoredToken_setsLoadingFalse', () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    // Should show "no user" immediately (isLoading=false, user=null)
    expect(screen.getByText('no user')).toBeInTheDocument()
    expect(mockTryRefreshToken).not.toHaveBeenCalled()
  })

  it('AuthContext_expiredToken_silentlyRefreshes', async () => {
    localStorage.setItem('access_token', EXPIRED_TOKEN)
    mockTryRefreshToken.mockResolvedValue(true)

    // After refresh succeeds, new token will be in localStorage
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem')
    getItemSpy.mockImplementation((key) => {
      if (key === 'access_token' && mockTryRefreshToken.mock.calls.length > 0) {
        return VALID_TOKEN
      }
      return EXPIRED_TOKEN
    })

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    // Should call tryRefreshToken
    await waitFor(() => expect(mockTryRefreshToken).toHaveBeenCalled())

    // Wait for the second effect to restore the session after refresh
    await waitFor(() => {
      const email = screen.queryByTestId('email')
      expect(email).toBeInTheDocument()
      expect(email).toHaveTextContent('test@example.com')
    })

    getItemSpy.mockRestore()
  })

  it('AuthContext_refreshFails_clearsToken', async () => {
    localStorage.setItem('access_token', EXPIRED_TOKEN)
    mockTryRefreshToken.mockResolvedValue(false)

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    // Should call tryRefreshToken
    await waitFor(() => expect(mockTryRefreshToken).toHaveBeenCalled())

    // Should show "no user" after failed refresh
    expect(screen.getByText('no user')).toBeInTheDocument()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

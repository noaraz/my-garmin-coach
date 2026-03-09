import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuthProvider, useAuth } from '../contexts/AuthContext'

const { mockLoginUser } = vi.hoisted(() => ({
  mockLoginUser: vi.fn().mockResolvedValue({
    access_token: 'header.eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.sig',
    refresh_token: 'refresh-token-value',
    token_type: 'bearer',
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, loginUser: mockLoginUser }
})

// A valid JWT payload: { userId: 1, email: "test@example.com", exp: 9999999999 }
// base64url-encoded: eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0
const VALID_TOKEN =
  'header.eyJ1c2VySWQiOjEsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.sig'

function AuthConsumer() {
  const { user, isLoading, logout } = useAuth()
  if (isLoading) return <div>loading</div>
  if (!user) return <div>no user</div>
  return (
    <div>
      <span data-testid="email">{user.email}</span>
      <button onClick={logout}>logout</button>
    </div>
  )
}

beforeEach(() => {
  localStorage.clear()
  mockLoginUser.mockReset()
  mockLoginUser.mockResolvedValue({
    access_token: VALID_TOKEN,
    refresh_token: 'refresh-token-value',
    token_type: 'bearer',
  })
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

  it('login_stores_tokens_and_sets_user', async () => {
    function LoginTrigger() {
      const { login, user } = useAuth()
      return (
        <div>
          <button onClick={() => login('test@example.com', 'pass')}>login</button>
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
    expect(localStorage.getItem('refresh_token')).toBe('refresh-token-value')
    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')
  })

  it('logout_clears_tokens', async () => {
    localStorage.setItem('access_token', VALID_TOKEN)
    localStorage.setItem('refresh_token', 'refresh-token-value')

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
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('initializes_from_localStorage_on_mount', async () => {
    localStorage.setItem('access_token', VALID_TOKEN)
    localStorage.setItem('refresh_token', 'refresh-token-value')

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    )

    expect(await screen.findByTestId('email')).toHaveTextContent('test@example.com')
  })
})

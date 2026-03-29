import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { SettingsPage } from '../pages/SettingsPage'

const { mockToggleTheme, mockIsMobile } = vi.hoisted(() => ({
  mockToggleTheme: vi.fn(),
  mockIsMobile: vi.fn().mockReturnValue(true),
}))

vi.mock('../contexts/ThemeContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/ThemeContext')>()
  return { ...actual, useTheme: () => ({ theme: 'dark' as const, toggleTheme: mockToggleTheme }) }
})

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    getGarminStatus: vi.fn().mockResolvedValue({ connected: false, credentials_stored: false }),
    connectGarmin: vi.fn(),
    disconnectGarmin: vi.fn(),
    createInvite: vi.fn().mockResolvedValue({ code: 'abc123' }),
  }
})

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: { id: 1, email: 'test@example.com' },
      accessToken: null,
      isAdmin: false,
      googleLogin: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    }),
  }
})

vi.mock('../contexts/GarminStatusContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/GarminStatusContext')>()
  return { ...actual, useGarminStatus: () => ({ garminConnected: false, refresh: vi.fn() }) }
})

vi.mock('../hooks/useIsMobile', () => ({ useIsMobile: () => mockIsMobile() }))

const renderPage = () =>
  render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>
  )

describe('SettingsPage — Display Settings (mobile)', () => {
  beforeEach(() => {
    mockToggleTheme.mockClear()
    mockIsMobile.mockReturnValue(true)
  })

  it('renders the Display Settings section heading on mobile', () => {
    renderPage()
    expect(screen.getByText(/display settings/i)).toBeInTheDocument()
  })

  it('renders a Theme row', () => {
    renderPage()
    expect(screen.getByText('Theme')).toBeInTheDocument()
  })

  it('shows "Dark" sub-label when theme is dark', () => {
    renderPage()
    expect(screen.getByText('Dark')).toBeInTheDocument()
  })

  it('calls toggleTheme when the toggle button is clicked', () => {
    renderPage()
    const toggleBtn = screen.getByRole('button', { name: /switch to light mode/i })
    fireEvent.click(toggleBtn)
    expect(mockToggleTheme).toHaveBeenCalledOnce()
  })
})

describe('SettingsPage — Display Settings (desktop)', () => {
  beforeEach(() => {
    mockIsMobile.mockReturnValue(false)
  })

  it('does NOT render the Display Settings section on desktop', () => {
    renderPage()
    expect(screen.queryByText(/display settings/i)).not.toBeInTheDocument()
  })
})

import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { Sidebar } from '../components/layout/Sidebar'
import { GarminStatusProvider } from '../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../contexts/ZonesStatusContext'

declare const __APP_VERSION__: string

const { mockGetGarminStatus, mockFetchProfile, mockNavigate } = vi.hoisted(() => ({
  mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: true }),
  mockFetchProfile: vi.fn().mockResolvedValue({ threshold_pace: null, lthr: null }),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, getGarminStatus: mockGetGarminStatus, fetchProfile: mockFetchProfile }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
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

vi.mock('../contexts/ThemeContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/ThemeContext')>()
  return {
    ...actual,
    useTheme: () => ({ theme: 'dark' as const, toggleTheme: vi.fn() }),
  }
})

beforeEach(() => {
  mockGetGarminStatus.mockReset()
  mockGetGarminStatus.mockResolvedValue({ connected: true })
  mockFetchProfile.mockReset()
  mockFetchProfile.mockResolvedValue({ threshold_pace: null, lthr: null })
  mockNavigate.mockReset()
})

const renderSidebar = () =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <Sidebar />
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </MemoryRouter>
  )

describe('Sidebar version display', () => {
  it('shows version with -dev suffix in test/dev mode', () => {
    renderSidebar()
    expect(screen.getByText(/^v\d+\.\d+\.\d+-dev$/)).toBeInTheDocument()
  })

  it('version number reflects package.json via __APP_VERSION__', () => {
    renderSidebar()
    expect(screen.getByText(new RegExp(`^v${__APP_VERSION__}`))).toBeInTheDocument()
  })
})

describe('Garmin status row', () => {
  it('shows Connected label when garminConnected is true', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    renderSidebar()
    expect(await screen.findByText('Connected')).toBeInTheDocument()
  })

  it('shows Not connected label when garminConnected is false', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: false })
    renderSidebar()
    expect(await screen.findByText('Not connected')).toBeInTheDocument()
  })

  it('clicking Garmin row navigates to /settings', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    const user = userEvent.setup()
    renderSidebar()
    const btn = await screen.findByRole('button', { name: /Garmin: Connected/i })
    await user.click(btn)
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
  })

  it('does not render Garmin row while loading (null)', async () => {
    mockGetGarminStatus.mockReturnValue(new Promise(() => {}))
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Connected')).not.toBeInTheDocument()
    expect(screen.queryByText('Not connected')).not.toBeInTheDocument()
  })
})

describe('Zones status indicator', () => {
  it('shows Not set label when threshold_pace is null', async () => {
    mockFetchProfile.mockResolvedValue({ threshold_pace: null, lthr: null })
    renderSidebar()
    expect(await screen.findByText('Not set')).toBeInTheDocument()
  })

  it('does not show Not set when threshold_pace is set', async () => {
    mockFetchProfile.mockResolvedValue({ threshold_pace: 280, lthr: 155 })
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Not set')).not.toBeInTheDocument()
  })

  it('does not show Not set while loading (null)', async () => {
    mockFetchProfile.mockReturnValue(new Promise(() => {}))
    renderSidebar()
    await act(async () => {})
    expect(screen.queryByText('Not set')).not.toBeInTheDocument()
  })
})

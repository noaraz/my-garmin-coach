import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { Sidebar } from '../components/layout/Sidebar'

declare const __APP_VERSION__: string

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

const renderSidebar = () => render(<MemoryRouter><Sidebar /></MemoryRouter>)

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

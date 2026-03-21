import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { HelpPage } from '../pages/HelpPage'

const { mockOpenWizard, mockCloseWizard } = vi.hoisted(() => ({
  mockOpenWizard: vi.fn(),
  mockCloseWizard: vi.fn(),
}))

vi.mock('../contexts/OnboardingContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/OnboardingContext')>()
  return {
    ...actual,
    useOnboarding: () => ({
      isWizardOpen: false,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    }),
  }
})

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return {
    ...actual,
    useAuth: () => ({
      user: { id: 1, email: 'test@example.com', isAdmin: false },
      accessToken: null,
      isAdmin: false,
      googleLogin: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    }),
  }
})

beforeEach(() => {
  localStorage.clear()
  mockOpenWizard.mockReset()
  mockCloseWizard.mockReset()
})

const renderPage = () =>
  render(
    <MemoryRouter>
      <HelpPage />
    </MemoryRouter>
  )

describe('HelpPage', () => {
  it('renders Help & Getting Started title', async () => {
    renderPage()
    expect(await screen.findByText('Help & Getting Started')).toBeInTheDocument()
  })

  it('renders Recommended Setup section with 3 cards', () => {
    renderPage()
    expect(screen.getByText('Connect Garmin')).toBeInTheDocument()
    expect(screen.getByText('Set Training Zones')).toBeInTheDocument()
    expect(screen.getByText('Build a Plan')).toBeInTheDocument()
  })

  it('renders Feature Overview with 6 feature cards', () => {
    renderPage()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Training Zones')).toBeInTheDocument()
    expect(screen.getByText('Calendar')).toBeInTheDocument()
    expect(screen.getByText('Builder')).toBeInTheDocument()
    expect(screen.getByText('Library')).toBeInTheDocument()
    // Plan Coach appears twice (setup card + feature card) — use getAllByText
    expect(screen.getAllByText('Plan Coach').length).toBeGreaterThanOrEqual(1)
  })

  it('Replay Tour button calls openWizard()', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /replay tour/i }))
    expect(mockOpenWizard).toHaveBeenCalledTimes(1)
  })

  it('Replay Tour clears localStorage key before opening wizard', async () => {
    localStorage.setItem('onboarding_completed_1', 'true')
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /replay tour/i }))
    expect(localStorage.getItem('onboarding_completed_1')).toBeNull()
    expect(mockOpenWizard).toHaveBeenCalled()
  })
})

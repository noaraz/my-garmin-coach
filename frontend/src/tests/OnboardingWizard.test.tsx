import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { OnboardingWizard } from '../components/onboarding/OnboardingWizard'

const { mockOpenWizard, mockCloseWizard, mockNavigate, mockUseAuth, mockUseOnboarding } =
  vi.hoisted(() => ({
    mockOpenWizard: vi.fn(),
    mockCloseWizard: vi.fn(),
    mockNavigate: vi.fn(),
    mockUseAuth: vi.fn(),
    mockUseOnboarding: vi.fn(),
  }))

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>()
  return { ...actual, useAuth: mockUseAuth }
})

vi.mock('../contexts/OnboardingContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/OnboardingContext')>()
  return { ...actual, useOnboarding: mockUseOnboarding }
})

beforeEach(() => {
  mockOpenWizard.mockReset()
  mockCloseWizard.mockReset()
  mockNavigate.mockReset()
  localStorage.clear()

  // Default: wizard closed
  mockUseOnboarding.mockReturnValue({
    isWizardOpen: false,
    openWizard: mockOpenWizard,
    closeWizard: mockCloseWizard,
  })

  // Default: user logged in with id 1
  mockUseAuth.mockReturnValue({
    user: { id: 1, email: 'test@example.com', isAdmin: false },
    accessToken: null,
    isAdmin: false,
    googleLogin: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
  })
})

const renderWizard = () =>
  render(
    <MemoryRouter>
      <OnboardingWizard />
    </MemoryRouter>,
  )

describe('OnboardingWizard', () => {
  test('wizard opens when localStorage key is absent', () => {
    // No key in localStorage
    renderWizard()

    expect(mockOpenWizard).toHaveBeenCalledTimes(1)
  })

  test('wizard does not open when localStorage key is present', () => {
    localStorage.setItem('onboarding_completed_1', '1')

    renderWizard()

    expect(mockOpenWizard).not.toHaveBeenCalled()
  })

  test('null-guard: openWizard not called when userId is undefined', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      accessToken: null,
      isAdmin: false,
      googleLogin: vi.fn(),
      logout: vi.fn(),
      isLoading: true,
    })

    renderWizard()

    expect(mockOpenWizard).not.toHaveBeenCalled()
  })

  test('Skip sets localStorage key and closes wizard', async () => {
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    const user = userEvent.setup()

    renderWizard()

    await user.click(screen.getByText('SKIP'))

    expect(localStorage.getItem('onboarding_completed_1')).toBe('1')
    expect(mockCloseWizard).toHaveBeenCalledTimes(1)
  })

  test('Next navigates to step 2 route (/settings)', async () => {
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    const user = userEvent.setup()

    renderWizard()

    await user.click(screen.getByText('Next →'))

    expect(mockNavigate).toHaveBeenCalledWith('/settings')
  })

  test('Finish on last step sets localStorage key and closes wizard', async () => {
    // We need to get to step 6 (last step) — click Next 6 times
    // But since navigate is mocked, we need the wizard to advance its internal step counter
    // Re-render with wizard open each time to simulate advancing
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    const user = userEvent.setup()

    renderWizard()

    // Click Next 6 times to reach the last step
    for (let i = 0; i < 6; i++) {
      await user.click(screen.getByText('Next →'))
    }

    // Now on last step, button should say "Finish"
    await user.click(screen.getByText('Finish'))

    expect(localStorage.getItem('onboarding_completed_1')).toBe('1')
    expect(mockCloseWizard).toHaveBeenCalledTimes(1)
  })

  test('wizard resets to step 0 when reopened', async () => {
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    const user = userEvent.setup()

    const { rerender } = render(
      <MemoryRouter>
        <OnboardingWizard />
      </MemoryRouter>,
    )

    // Advance to step 3
    await user.click(screen.getByText('Next →'))
    await user.click(screen.getByText('Next →'))
    await user.click(screen.getByText('Next →'))

    // Close wizard
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: false,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    await act(async () => {
      rerender(
        <MemoryRouter>
          <OnboardingWizard />
        </MemoryRouter>,
      )
    })

    // Reopen wizard
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })
    await act(async () => {
      rerender(
        <MemoryRouter>
          <OnboardingWizard />
        </MemoryRouter>,
      )
    })

    // Should be on step 1 of 7 (reset to step 0)
    expect(screen.getByText('Step 1 of 7')).toBeInTheDocument()
  })

  test('OnboardingWizard_onMobile_isFullScreen', () => {
    // Override matchMedia to simulate mobile
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true, // mobile
      media: '(max-width: 767px)',
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })

    // Render wizard in open state
    mockUseOnboarding.mockReturnValue({
      isWizardOpen: true,
      openWizard: mockOpenWizard,
      closeWizard: mockCloseWizard,
    })

    renderWizard()

    const dialog = screen.getByRole('dialog')
    // Bottom sheet: position fixed, from bottom, 90vh, rounded top corners
    // The dialog itself is the overlay, we need to check its first child (the card)
    const modalCard = dialog.firstElementChild as HTMLElement
    expect(modalCard).toHaveStyle({ position: 'fixed' })
    expect(modalCard).toHaveStyle({ borderRadius: '20px 20px 0 0' })
  })
})

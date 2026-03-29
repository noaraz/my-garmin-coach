import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'

import type { ReactNode } from 'react'

// Mock contexts that AppShell's providers depend on
vi.mock('../api/client', () => ({
  getGarminStatus: vi.fn().mockResolvedValue({ connected: false, credentials_stored: false }),
  fetchProfile: vi.fn().mockResolvedValue(null),
}))

vi.mock('../contexts/OnboardingContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/OnboardingContext')>()
  return {
    ...actual,
    OnboardingProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  }
})

vi.mock('../components/onboarding/OnboardingWizard', () => ({
  OnboardingWizard: () => null,
}))

function mockMatchMedia(isMobile: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: isMobile,
    media: '(max-width: 767px)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })
}

const renderShell = () =>
  render(
    <MemoryRouter>
      <AppShell>
        <div data-testid="child">content</div>
      </AppShell>
    </MemoryRouter>
  )

describe('AppShell', () => {
  beforeEach(() => {
    // Reset to desktop by default so tests don't bleed into each other
    mockMatchMedia(false)
  })

  it('AppShell_onDesktop_rendersSidebar', () => {
    mockMatchMedia(false)
    renderShell()
    // Sidebar.tsx root element is <aside> (ARIA role = complementary)
    expect(screen.getByRole('complementary', { name: /sidebar/i })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /bottom tab/i })).not.toBeInTheDocument()
  })

  it('AppShell_onMobile_rendersBottomTabBar', () => {
    mockMatchMedia(true)
    renderShell()
    expect(screen.queryByRole('complementary', { name: /sidebar/i })).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: /bottom tab/i })).toBeInTheDocument()
  })

  it('AppShell_alwaysRendersChildren', () => {
    mockMatchMedia(false)
    renderShell()
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })
})

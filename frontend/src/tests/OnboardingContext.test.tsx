import { render, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { OnboardingProvider, useOnboarding } from '../contexts/OnboardingContext'

const wrapper = ({ children }: { children: ReactNode }) => (
  <OnboardingProvider>{children}</OnboardingProvider>
)

describe('OnboardingContext', () => {
  test('openWizard when called sets isWizardOpen to true', () => {
    const { result } = renderHook(() => useOnboarding(), { wrapper })

    expect(result.current.isWizardOpen).toBe(false)

    act(() => { result.current.openWizard() })

    expect(result.current.isWizardOpen).toBe(true)
  })

  test('closeWizard when wizard is open sets isWizardOpen to false', () => {
    const { result } = renderHook(() => useOnboarding(), { wrapper })

    act(() => { result.current.openWizard() })
    expect(result.current.isWizardOpen).toBe(true)

    act(() => { result.current.closeWizard() })

    expect(result.current.isWizardOpen).toBe(false)
  })

  test('useOnboarding when used outside OnboardingProvider throws', () => {
    function NoProvider() {
      useOnboarding()
      return null
    }

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      expect(() => render(<NoProvider />)).toThrow(
        'useOnboarding must be used inside OnboardingProvider',
      )
    } finally {
      consoleError.mockRestore()
    }
  })
})

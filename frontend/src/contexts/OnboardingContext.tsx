import { createContext, useContext, useState, type ReactNode } from 'react'

interface OnboardingContextValue {
  isWizardOpen: boolean
  openWizard: () => void
  closeWizard: () => void
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null)

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [isWizardOpen, setIsWizardOpen] = useState<boolean>(false)

  const openWizard = () => setIsWizardOpen(true)
  const closeWizard = () => setIsWizardOpen(false)

  return (
    <OnboardingContext.Provider value={{ isWizardOpen, openWizard, closeWizard }}>
      {children}
    </OnboardingContext.Provider>
  )
}

export function useOnboarding(): OnboardingContextValue {
  const ctx = useContext(OnboardingContext)
  if (!ctx) throw new Error('useOnboarding must be used inside OnboardingProvider')
  return ctx
}

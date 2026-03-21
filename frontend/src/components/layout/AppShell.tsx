import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { GarminStatusProvider } from '../../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../../contexts/ZonesStatusContext'
import { OnboardingProvider } from '../../contexts/OnboardingContext'
import { OnboardingWizard } from '../onboarding/OnboardingWizard'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <OnboardingProvider>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
            <Sidebar />
            <OnboardingWizard />
            <main style={{
              flex: 1,
              overflow: 'auto',
              background: 'var(--bg-main)',
              display: 'flex',
              flexDirection: 'column',
            }}>
              {children}
            </main>
          </div>
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </OnboardingProvider>
  )
}

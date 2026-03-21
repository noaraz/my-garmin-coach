import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { BottomTabBar } from './BottomTabBar'
import { GarminStatusProvider } from '../../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../../contexts/ZonesStatusContext'
import { OnboardingProvider } from '../../contexts/OnboardingContext'
import { OnboardingWizard } from '../onboarding/OnboardingWizard'
import { useIsMobile } from '../../hooks/useIsMobile'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const isMobile = useIsMobile()

  return (
    <OnboardingProvider>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
            {!isMobile && <Sidebar />}
            <OnboardingWizard />
            <main
              style={{
                flex: 1,
                overflow: 'auto',
                background: 'var(--bg-main)',
                display: 'flex',
                flexDirection: 'column',
                paddingBottom: isMobile ? 'var(--bottom-tab-height)' : undefined,
              }}
            >
              {children}
            </main>
            {isMobile && <BottomTabBar />}
          </div>
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </OnboardingProvider>
  )
}

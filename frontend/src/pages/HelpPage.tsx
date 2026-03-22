import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useOnboarding } from '../contexts/OnboardingContext'
import { useIsMobile } from '../hooks/useIsMobile'

const setupSteps = [
  {
    number: 1,
    title: 'Connect Garmin',
    description: 'Link your Garmin account first so workouts sync to your watch.',
    destination: 'Settings',
  },
  {
    number: 2,
    title: 'Set Training Zones',
    description: 'Enter LTHR and threshold pace. All workout targets derive from these.',
    destination: 'Zones',
  },
  {
    number: 3,
    title: 'Build a Plan',
    description: 'Import a multi-week CSV plan or generate one with AI.',
    destination: 'Plan Coach',
  },
]

const features = [
  { icon: '⚙️', title: 'Settings', description: 'Connect Garmin, manage invite codes' },
  { icon: '📊', title: 'Training Zones', description: 'Configure HR and pace zones' },
  { icon: '📅', title: 'Calendar', description: 'Schedule workouts, track compliance' },
  { icon: '🔨', title: 'Builder', description: 'Create structured, zone-based workouts' },
  { icon: '📚', title: 'Library', description: 'Browse and reuse saved workout templates' },
  { icon: '🤖', title: 'Plan Coach', description: 'Import or AI-generate multi-week training plans' },
]

const sectionLabelStyle: CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontSize: '11px',
  fontWeight: 700,
  color: 'var(--text-muted)',
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  marginBottom: '12px',
}

export function HelpPage() {
  const { user } = useAuth()
  const { openWizard } = useOnboarding()
  const isMobile = useIsMobile()
  const navigate = useNavigate()

  const handleReplay = () => {
    if (user?.id) {
      localStorage.removeItem(`onboarding_completed_${user.id}`)
    }
    openWizard()
  }

  const content = (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: isMobile ? '0' : '0' }}>
      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h1 style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: isMobile ? '18px' : '24px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 4px',
            lineHeight: 1.2,
          }}>
            Help & Getting Started
          </h1>
          <p style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '13px',
            color: 'var(--text-secondary)',
            margin: 0,
          }}>
            Everything you need to set up and use GarminCoach.
          </p>
        </div>
        <button
          aria-label="Replay Tour"
          onClick={handleReplay}
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            background: 'transparent',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
            padding: '6px 12px',
            borderRadius: '5px',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          Replay Tour
        </button>
      </div>

        {/* Section 1 — Setup Guide */}
        <section style={{ marginBottom: isMobile ? '20px' : '40px' }}>
          <div style={sectionLabelStyle}>Recommended Setup</div>
          <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '12px' }}>
            {setupSteps.map((step) => (
              <div
                key={step.number}
                style={{
                  flex: 1,
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '16px',
                }}
              >
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: 'var(--accent)',
                  color: 'var(--text-on-accent)',
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '10px',
                  flexShrink: 0,
                }}>
                  {step.number}
                </div>
                <div style={{
                  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                  fontSize: '14px',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  marginBottom: '6px',
                }}>
                  {step.title}
                </div>
                <div style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.45,
                  marginBottom: '10px',
                }}>
                  {step.description}
                </div>
                <div style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  letterSpacing: '0.04em',
                }}>
                  → {step.destination}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Section 2 — Feature Overview */}
        <section>
          <div style={sectionLabelStyle}>Features</div>
          <div
            data-testid="feature-cards-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
              gap: '12px',
            }}
          >
            {features.map((feature) => (
              <div
                key={feature.title}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  padding: '12px',
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'flex-start',
                }}
              >
                <span style={{ fontSize: '20px', lineHeight: 1, flexShrink: 0 }}>
                  {feature.icon}
                </span>
                <div>
                  <div style={{
                    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                    fontSize: '13px',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    marginBottom: '3px',
                  }}>
                    {feature.title}
                  </div>
                  <div style={{
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.4,
                  }}>
                    {feature.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
    </div>
  )

  if (isMobile) {
    return (
      <>
        {/* Backdrop */}
        <div
          onClick={() => navigate(-1)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 200,
          }}
        />
        {/* Bottom sheet */}
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            height: '85vh',
            background: 'var(--bg-surface)',
            borderRadius: '20px 20px 0 0',
            zIndex: 201,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            animation: 'slideUpSheet 280ms ease-out',
          }}
        >
          {/* Handle + header row */}
          <div style={{ flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
              <div style={{ width: 32, height: 4, borderRadius: 2, background: 'var(--border)' }} />
            </div>
          </div>
          {/* Scrollable content */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px 20px',
            paddingBottom: 'calc(var(--bottom-tab-height) + 16px)',
          }}>
            {content}
          </div>
        </div>
      </>
    )
  }

  return (
    <div className="mobile-page-content" style={{ padding: '32px 40px' }}>
      {content}
    </div>
  )
}

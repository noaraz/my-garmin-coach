import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useOnboarding } from '../../contexts/OnboardingContext'
import { useIsMobile } from '../../hooks/useIsMobile'

interface StepConfig {
  route: string
  title: string
  description: string
}

const STEPS: StepConfig[] = [
  {
    route: '/calendar',
    title: 'Welcome to GarminCoach',
    description:
      'Get started with your personal training platform. We recommend this setup order: Connect Garmin → Set Zones → Build a Plan.',
  },
  {
    route: '/settings',
    title: 'Connect Garmin',
    description:
      'Start here — link your Garmin account so workouts sync directly to your watch.',
  },
  {
    route: '/zones',
    title: 'Set Your Training Zones',
    description:
      'Enter your LTHR and threshold pace. All workout targets derive from these zones.',
  },
  {
    route: '/calendar',
    title: 'Your Training Calendar',
    description:
      'Schedule workouts week by week. Click any workout to open the detail panel and take actions.',
  },
  {
    route: '/builder',
    title: 'Build Workouts',
    description:
      'Create structured, zone-based workouts with the visual builder.',
  },
  {
    route: '/library',
    title: 'Workout Library',
    description:
      'Browse your saved workout templates. Reuse them across training blocks.',
  },
  {
    route: '/plan-coach',
    title: 'Plan Coach',
    description:
      'Import a multi-week training plan via CSV, or generate one with AI.',
  },
]

const buttonStyle: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  padding: '8px 16px',
  borderRadius: '4px',
  cursor: 'pointer',
}

export function OnboardingWizard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isWizardOpen, openWizard, closeWizard } = useOnboarding()
  const [step, setStep] = useState(0)
  const isMobile = useIsMobile()

  // Open wizard on mount if key is absent
  useEffect(() => {
    if (user?.id === undefined) return
    const key = `onboarding_completed_${user.id}`
    if (localStorage.getItem(key) === null) {
      openWizard()
    }
  }, [user?.id, openWizard])

  // Reset to step 0 when wizard opens
  useEffect(() => {
    if (isWizardOpen) {
      setStep(0)
    }
  }, [isWizardOpen])

  if (!isWizardOpen) return null
  if (!user) return null

  const handleComplete = () => {
    localStorage.setItem(`onboarding_completed_${user.id}`, '1')
    closeWizard()
  }

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      const nextStep = step + 1
      setStep(nextStep)
      navigate(STEPS[nextStep].route)
    } else {
      handleComplete()
    }
  }

  const handleBack = () => {
    if (step > 0) {
      const prevStep = step - 1
      setStep(prevStep)
      navigate(STEPS[prevStep].route)
    }
  }

  const isLastStep = step === STEPS.length - 1

  const modalCardStyle: CSSProperties = isMobile
    ? {
        // Mobile: 90vh bottom sheet — slides up from bottom
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: '90vh',
        background: 'var(--bg-surface)',
        borderRadius: '20px 20px 0 0',
        zIndex: 201,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'slideUpSheet 280ms ease-out',
        padding: '0 32px 32px 32px',
      }
    : {
        // Desktop: centered modal card
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '32px',
        maxWidth: '480px',
        width: '100%',
      }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay-bg)',
        zIndex: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={modalCardStyle}>
        {/* Handle bar (mobile only) */}
        {isMobile && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px', flexShrink: 0 }}>
            <div style={{ width: 32, height: 4, borderRadius: 2, background: 'var(--border)' }} />
          </div>
        )}

        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}
          >
            Step {step + 1} of {STEPS.length}
          </span>
          <button
            onClick={handleComplete}
            style={{
              ...buttonStyle,
              border: 'none',
              background: 'transparent',
              color: 'var(--text-muted)',
            }}
          >
            SKIP
          </button>
        </div>

        {/* Title */}
        <h2
          id="onboarding-title"
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '20px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginTop: '16px',
            marginBottom: 0,
          }}
        >
          {STEPS[step].title}
        </h2>

        {/* Description */}
        <p
          style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '14px',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            marginTop: '12px',
            marginBottom: 0,
          }}
        >
          {STEPS[step].description}
        </p>

        {/* Progress dots */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'row',
            gap: '6px',
            marginTop: '24px',
            marginBottom: '24px',
          }}
        >
          {STEPS.map((_, i) => (
            <div
              key={i}
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: i === step ? 'var(--accent)' : 'var(--border)',
              }}
            />
          ))}
        </div>

        {/* Footer row */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          {step > 0 && (
            <button
              onClick={handleBack}
              style={{
                ...buttonStyle,
                border: '1px solid var(--border)',
                background: 'transparent',
                color: 'var(--text-secondary)',
              }}
            >
              Back
            </button>
          )}
          {isLastStep ? (
            <button
              onClick={handleComplete}
              style={{
                ...buttonStyle,
                border: 'none',
                background: 'var(--accent)',
                color: 'var(--text-on-accent)',
              }}
            >
              Finish
            </button>
          ) : (
            <button
              onClick={handleNext}
              style={{
                ...buttonStyle,
                border: 'none',
                background: 'var(--accent)',
                color: 'var(--text-on-accent)',
              }}
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

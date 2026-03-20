import { useState } from 'react'
import { CsvImportTab } from '../components/plan-coach/CsvImportTab'

type Tab = 'plan' | 'chat'

const pageTitle: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '22px',
  letterSpacing: '0.04em',
  color: 'var(--text-primary)',
  marginBottom: '4px',
}

const pageSubtitle: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
  fontSize: '13px',
  color: 'var(--text-muted)',
  marginBottom: '24px',
}

const tabStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  padding: '7px 16px',
  background: 'transparent',
  border: 'none',
  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
  color: active ? 'var(--accent)' : disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.5 : 1,
  transition: 'color 0.12s, border-color 0.12s',
})

export function PlanCoachPage() {
  const [activeTab, setActiveTab] = useState<Tab>('plan')

  return (
    <div style={{
      padding: '32px 36px',
      maxWidth: '860px',
      margin: '0 auto',
    }}>
      <h1 style={pageTitle}>Plan Coach</h1>
      <p style={pageSubtitle}>
        Import a multi-week training plan from CSV or generate one with AI.
      </p>

      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border)',
        marginBottom: '24px',
        gap: '2px',
      }}>
        <button
          role="tab"
          aria-selected={activeTab === 'plan'}
          onClick={() => setActiveTab('plan')}
          style={tabStyle(activeTab === 'plan', false)}
        >
          Plan
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'chat'}
          disabled
          style={tabStyle(activeTab === 'chat', true)}
          title="Coming soon — Phase 4"
        >
          Chat (coming soon)
        </button>
      </div>

      {/* Tab content */}
      {activeTab === 'plan' && <CsvImportTab />}
    </div>
  )
}

import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// SVG icons — inline to avoid extra files
const TodayIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
)
const CalendarIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)
const LibraryIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"/>
    <line x1="8" y1="12" x2="21" y2="12"/>
    <line x1="8" y1="18" x2="21" y2="18"/>
    <line x1="3" y1="6" x2="3.01" y2="6"/>
    <line x1="3" y1="12" x2="3.01" y2="12"/>
    <line x1="3" y1="18" x2="3.01" y2="18"/>
  </svg>
)
const ZonesIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
)
const MoreIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5" cy="12" r="1" fill="currentColor"/>
    <circle cx="12" cy="12" r="1" fill="currentColor"/>
    <circle cx="19" cy="12" r="1" fill="currentColor"/>
  </svg>
)

// More sheet items
const MORE_ITEMS: Array<{ label: string; route: string }> = [
  { label: 'Builder',    route: '/builder' },
  { label: 'Plan Coach', route: '/plan-coach' },
  { label: 'Settings',   route: '/settings' },
  { label: 'Help',       route: '/help' },
]

// Primary tabs
const TABS = [
  { label: 'Today',    route: '/today',    Icon: TodayIcon },
  { label: 'Calendar', route: '/calendar', Icon: CalendarIcon },
  { label: 'Library',  route: '/library',  Icon: LibraryIcon },
  { label: 'Zones',    route: '/zones',    Icon: ZonesIcon },
]

export function BottomTabBar() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)

  const tabStyle = (active: boolean): CSSProperties => ({
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    padding: '6px 0 4px',
    color: active ? 'var(--accent)' : 'var(--text-muted)',
    fontSize: 9,
    fontFamily: 'var(--font-family-display)',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    transition: 'color 120ms',
  })

  const moreItemStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    padding: '14px 20px',
    border: 'none',
    borderBottom: '1px solid var(--border)',
    background: 'none',
    cursor: 'pointer',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-family-body)',
    fontSize: 16,
    textAlign: 'left',
  }

  return (
    <>
      {moreOpen && (
        <>
          <div
            data-testid="more-sheet-backdrop"
            className="mobile-bottom-sheet-backdrop"
            onClick={() => setMoreOpen(false)}
          />
          <div className="mobile-bottom-sheet">
            <div style={{ padding: '12px 20px 8px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontFamily: 'var(--font-family-display)', fontWeight: 700, fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                More
              </span>
            </div>
            {MORE_ITEMS.map(({ label, route }) => (
              <button
                key={route}
                style={moreItemStyle}
                onClick={() => { setMoreOpen(false); navigate(route) }}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}

      <nav
        aria-label="Bottom tab bar"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          height: 'var(--bottom-tab-height)',
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          zIndex: 100,
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        {TABS.map(({ label, route, Icon }) => {
          const active = pathname === route || (route === '/today' && pathname === '/')
          return (
            <button
              key={route}
              aria-label={label}
              style={tabStyle(active)}
              onClick={() => navigate(route)}
            >
              <Icon />
              {label}
            </button>
          )
        })}
        <button
          aria-label="More"
          style={tabStyle(moreOpen)}
          onClick={() => setMoreOpen(v => !v)}
        >
          <MoreIcon />
          More
        </button>
      </nav>
    </>
  )
}

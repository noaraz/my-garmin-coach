import { NavLink } from 'react-router-dom'
import { useTheme } from '../../contexts/ThemeContext'

const CalendarIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
)

const ZonesIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
)

const BuilderIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
)

const LibraryIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"/>
    <line x1="8" y1="12" x2="21" y2="12"/>
    <line x1="8" y1="18" x2="21" y2="18"/>
    <line x1="3" y1="6" x2="3.01" y2="6"/>
    <line x1="3" y1="12" x2="3.01" y2="12"/>
    <line x1="3" y1="18" x2="3.01" y2="18"/>
  </svg>
)

export function Sidebar() {
  const { theme, toggleTheme } = useTheme()
  const navStyle = (isActive: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: '9px',
    padding: '7px 10px',
    borderRadius: '5px',
    marginBottom: '1px',
    fontSize: '12px',
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontWeight: 600,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    color: isActive ? '#ffffff' : '#5a5a5a',
    background: isActive ? 'rgba(255,255,255,0.09)' : 'transparent',
    transition: 'color 0.12s, background 0.12s',
  })

  return (
    <aside style={{
      width: '210px',
      minWidth: '210px',
      background: '#0d0d0d',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      borderRight: '1px solid #222',
    }}>
      {/* Logo area */}
      <div style={{
        padding: '18px 14px 14px',
        borderBottom: '1px solid #1e1e1e',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <div style={{
          width: '30px',
          height: '30px',
          background: '#0057ff',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          {/* Pulse/heartbeat icon */}
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div>
          <div style={{
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '14px',
            letterSpacing: '0.08em',
            color: '#fff',
            textTransform: 'uppercase',
            lineHeight: 1.15,
          }}>GarminCoach</div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '9px',
            color: '#3a3a3a',
            letterSpacing: '0.05em',
            marginTop: '1px',
          }}>TRAINING PLATFORM</div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '10px 8px', flex: 1 }}>
        <NavLink to="/calendar" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : '#5a5a5a', display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <CalendarIcon />
              Calendar
            </span>
          )}
        </NavLink>
        <NavLink to="/zones" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : '#5a5a5a', display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <ZonesIcon />
              Zones
            </span>
          )}
        </NavLink>
        <NavLink to="/builder" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : '#5a5a5a', display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <BuilderIcon />
              Builder
            </span>
          )}
        </NavLink>
        <NavLink to="/library" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : '#5a5a5a', display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <LibraryIcon />
              Library
            </span>
          )}
        </NavLink>
      </nav>

      {/* Theme toggle + version */}
      <div style={{
        padding: '10px 14px',
        borderTop: '1px solid #1a1a1a',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '9px',
          color: '#2e2e2e',
          letterSpacing: '0.06em',
        }}>v0.1.0-dev</span>
        <button
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          onClick={toggleTheme}
          title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: '#4a4a4a',
            padding: '2px',
            display: 'flex',
            alignItems: 'center',
            borderRadius: '3px',
            transition: 'color 0.15s',
          }}
        >
          {theme === 'light' ? (
            /* Moon icon */
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          ) : (
            /* Sun icon */
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          )}
        </button>
      </div>
    </aside>
  )
}

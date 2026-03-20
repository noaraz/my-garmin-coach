import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useTheme } from '../../contexts/ThemeContext'
import { useAuth } from '../../contexts/AuthContext'
import { useGarminStatus } from '../../contexts/GarminStatusContext'
import { useZonesStatus } from '../../contexts/ZonesStatusContext'

declare const __APP_VERSION__: string

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

const PlanCoachIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <line x1="3" y1="9" x2="21" y2="9"/>
    <line x1="9" y1="21" x2="9" y2="9"/>
  </svg>
)

const SettingsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
)

/* Sidebar is intentionally always dark — uses its own palette, not theme tokens */
const SIDE_BG    = '#18181c'
const SIDE_BORD  = '#2a2a30'
const SIDE_LOGO_SUB = '#505060'
const SIDE_VER   = '#42424e'
const SIDE_ICON_INACTIVE = '#6a6a78'
const SIDE_GARMIN_CONNECTED    = '#22c55e'
const SIDE_GARMIN_DISCONNECTED = '#ef4444'
const SIDE_ZONES_WARN          = '#f59e0b'

export function Sidebar() {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { garminConnected } = useGarminStatus()
  const { zonesConfigured } = useZonesStatus()
  const [garminHovered, setGarminHovered] = useState(false)
  const navStyle = (isActive: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: '9px',
    padding: '7px 10px',
    borderRadius: '5px',
    marginBottom: '1px',
    fontSize: '12px',
    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
    fontWeight: 600,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    textDecoration: 'none',
    color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE,
    background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
    transition: 'color 0.12s, background 0.12s',
  })

  return (
    <aside style={{
      width: '210px',
      minWidth: '210px',
      background: SIDE_BG,
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      borderRight: `1px solid ${SIDE_BORD}`,
    }}>
      {/* Logo area */}
      <div style={{
        padding: '18px 14px 14px',
        borderBottom: `1px solid ${SIDE_BORD}`,
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
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div>
          <div style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '14px',
            letterSpacing: '0.08em',
            color: '#fff',
            textTransform: 'uppercase',
            lineHeight: 1.15,
          }}>GarminCoach</div>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '9px',
            color: SIDE_LOGO_SUB,
            letterSpacing: '0.05em',
            marginTop: '1px',
          }}>TRAINING PLATFORM</div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '10px 8px', flex: 1 }}>
        <NavLink to="/calendar" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <CalendarIcon />
              Calendar
            </span>
          )}
        </NavLink>
        <NavLink to="/zones" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <ZonesIcon />
              Zones
              {zonesConfigured === false && (
                <>
                  <div style={{ marginLeft: 'auto', marginRight: '4px', width: '7px', height: '7px', borderRadius: '50%', background: SIDE_ZONES_WARN, boxShadow: '0 0 0 2px rgba(245,158,11,0.2)', flexShrink: 0 }} />
                  <span style={{ fontSize: '9px', fontWeight: 700, letterSpacing: '0.06em', color: SIDE_ZONES_WARN, marginLeft: 0 }}>Not set</span>
                </>
              )}
            </span>
          )}
        </NavLink>
        <NavLink to="/builder" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <BuilderIcon />
              Builder
            </span>
          )}
        </NavLink>
        <NavLink to="/library" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <LibraryIcon />
              Library
            </span>
          )}
        </NavLink>
        <NavLink to="/plan-coach" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <PlanCoachIcon />
              Plan Coach
            </span>
          )}
        </NavLink>
        <NavLink to="/settings" style={({ isActive }) => navStyle(isActive)}>
          {({ isActive }) => (
            <span style={{ color: isActive ? '#ffffff' : SIDE_ICON_INACTIVE, display: 'flex', alignItems: 'center', gap: '9px', width: '100%' }}>
              <SettingsIcon />
              Settings
            </span>
          )}
        </NavLink>
        {garminConnected !== null && (
          <button
            aria-label={garminConnected ? 'Garmin: Connected – go to Settings' : 'Garmin: Not connected – go to Settings'}
            onClick={() => navigate('/settings')}
            onMouseEnter={() => setGarminHovered(true)}
            onMouseLeave={() => setGarminHovered(false)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '9px',
              padding: '7px 10px',
              borderRadius: '5px',
              marginBottom: '1px',
              fontSize: '12px',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: SIDE_ICON_INACTIVE,
              background: garminHovered ? 'rgba(255,255,255,0.05)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              width: '100%',
              textAlign: 'left',
              transition: 'background 0.12s',
            }}
          >
            <div style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: garminConnected ? SIDE_GARMIN_CONNECTED : SIDE_GARMIN_DISCONNECTED,
              boxShadow: garminConnected
                ? '0 0 0 2px rgba(34,197,94,0.2)'
                : '0 0 0 2px rgba(239,68,68,0.2)',
              flexShrink: 0,
            }} />
            Garmin
            <span style={{
              marginLeft: 'auto',
              fontSize: '9px',
              fontWeight: 700,
              letterSpacing: '0.06em',
              color: garminConnected ? SIDE_GARMIN_CONNECTED : SIDE_GARMIN_DISCONNECTED,
            }}>
              {garminConnected ? 'Connected' : 'Not connected'}
            </span>
          </button>
        )}
      </nav>

      {/* User info + logout */}
      {user && (
        <div style={{
          padding: '10px 14px',
          borderTop: `1px solid ${SIDE_BORD}`,
        }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '9px',
            color: SIDE_LOGO_SUB,
            letterSpacing: '0.04em',
            marginBottom: '7px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap' as const,
          }}>
            {user.email}
          </div>
          <button
            aria-label="Log out"
            onClick={() => { logout(); navigate('/login') }}
            style={{
              background: 'transparent',
              border: `1px solid ${SIDE_BORD}`,
              cursor: 'pointer',
              color: SIDE_ICON_INACTIVE,
              padding: '4px 8px',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              borderRadius: '4px',
              fontSize: '10px',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase' as const,
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Log out
          </button>
        </div>
      )}

      {/* Theme toggle + version */}
      <div style={{
        padding: '10px 14px',
        borderTop: `1px solid ${SIDE_BORD}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '9px',
          color: SIDE_VER,
          letterSpacing: '0.06em',
        }}>{import.meta.env.PROD ? `v${__APP_VERSION__}` : `v${__APP_VERSION__}-dev`}</span>
        <button
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          onClick={toggleTheme}
          title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: SIDE_ICON_INACTIVE,
            padding: '2px',
            display: 'flex',
            alignItems: 'center',
            borderRadius: '3px',
            transition: 'color 0.15s',
          }}
        >
          {theme === 'light' ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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

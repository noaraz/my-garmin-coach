import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { bootstrapAdmin, resetAdmins } from '../api/client'

export function SetupPage() {
  const [setupToken, setSetupToken] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [resetMsg, setResetMsg] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await bootstrapAdmin(setupToken, email, password)
      setSuccess(true)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Setup failed'
      if (message.includes('409') || message.toLowerCase().includes('admin already exists')) {
        setError('Admin already exists. Please sign in.')
      } else if (message.includes('403')) {
        setError('Invalid setup token.')
      } else {
        setError(message)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = async () => {
    if (!confirmReset) {
      setConfirmReset(true)
      return
    }
    setIsResetting(true)
    setError(null)
    setResetMsg(null)
    try {
      const res = await resetAdmins(setupToken)
      setConfirmReset(false)
      setResetMsg(`Removed ${res.deleted} user${res.deleted !== 1 ? 's' : ''}. You can now run setup again.`)
    } catch (err) {
      setConfirmReset(false)
      const message = err instanceof Error ? err.message : 'Reset failed'
      if (message.includes('403')) {
        setError('Invalid setup token.')
      } else {
        setError(message)
      }
    } finally {
      setIsResetting(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-main)',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '380px',
        padding: '0 16px',
      }}>
        {/* Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '32px',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '34px',
            height: '34px',
            background: 'var(--accent)',
            borderRadius: '7px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-on-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div style={{
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '20px',
            letterSpacing: '0.08em',
            color: 'var(--text-primary)',
            textTransform: 'uppercase' as const,
          }}>GarminCoach</div>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '28px 24px',
        }}>
          <h1 style={{
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '20px',
            letterSpacing: '0.06em',
            textTransform: 'uppercase' as const,
            color: 'var(--text-primary)',
            margin: '0 0 20px',
          }}>First-Time Setup</h1>

          {success ? (
            <div>
              <p style={{
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontFamily: "'Barlow', system-ui, sans-serif",
                marginBottom: '16px',
              }}>
                Setup complete. Sign in to continue.
              </p>
              <Link
                to="/login"
                style={{
                  color: 'var(--accent)',
                  textDecoration: 'none',
                  fontWeight: 500,
                  fontSize: '14px',
                  fontFamily: "'Barlow', system-ui, sans-serif",
                }}
              >
                Sign in →
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate action="." method="post">
              <div style={{ marginBottom: '14px' }}>
                <label
                  htmlFor="setup-token"
                  style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase' as const,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  }}
                >
                  Setup Token
                </label>
                <input
                  id="setup-token"
                  name="setup-token"
                  type="password"
                  autoComplete="off"
                  value={setupToken}
                  onChange={e => setSetupToken(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '9px 11px',
                    background: 'var(--input-bg)',
                    border: '1px solid var(--input-border)',
                    borderRadius: '5px',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                    outline: 'none',
                    boxSizing: 'border-box' as const,
                  }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label
                  htmlFor="email"
                  style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase' as const,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  }}
                >
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '9px 11px',
                    background: 'var(--input-bg)',
                    border: '1px solid var(--input-border)',
                    borderRadius: '5px',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                    outline: 'none',
                    boxSizing: 'border-box' as const,
                  }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label
                  htmlFor="password"
                  style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase' as const,
                    color: 'var(--text-secondary)',
                    marginBottom: '6px',
                    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  }}
                >
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '9px 11px',
                    background: 'var(--input-bg)',
                    border: '1px solid var(--input-border)',
                    borderRadius: '5px',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                    outline: 'none',
                    boxSizing: 'border-box' as const,
                  }}
                />
              </div>

              {error && (
                <div
                  role="alert"
                  style={{
                    marginBottom: '14px',
                    padding: '9px 11px',
                    background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.3)',
                    borderRadius: '5px',
                    fontSize: '12px',
                    color: '#ef4444',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                  }}
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '10px',
                  background: isSubmitting ? 'var(--border-strong)' : 'var(--accent)',
                  color: 'var(--text-on-accent)',
                  border: 'none',
                  borderRadius: '5px',
                  fontSize: '12px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase' as const,
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {isSubmitting ? 'Creating…' : 'Create Admin'}
              </button>
            </form>
          )}

          {/* Danger zone — always visible */}
          {!success && (
            <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border)' }}>
              <div style={{
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase' as const,
                color: 'var(--text-muted)',
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                marginBottom: '10px',
              }}>
                Danger Zone
              </div>

              {resetMsg && (
                <div style={{
                  marginBottom: '10px',
                  padding: '9px 11px',
                  background: 'rgba(34,197,94,0.08)',
                  border: '1px solid rgba(34,197,94,0.3)',
                  borderRadius: '5px',
                  fontSize: '12px',
                  color: '#22c55e',
                  fontFamily: "'Barlow', system-ui, sans-serif",
                }}>
                  {resetMsg}
                </div>
              )}

              <button
                type="button"
                onClick={handleReset}
                disabled={isResetting}
                style={{
                  padding: '8px 16px',
                  background: confirmReset ? 'rgba(239,68,68,0.15)' : 'transparent',
                  color: '#ef4444',
                  border: '1px solid rgba(239,68,68,0.4)',
                  borderRadius: '5px',
                  fontSize: '11px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase' as const,
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  cursor: isResetting ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {isResetting ? 'Removing…' : confirmReset ? 'Confirm Remove All Admins' : 'Remove All Admins'}
              </button>

              {confirmReset && (
                <div style={{
                  marginTop: '6px',
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  fontFamily: "'Barlow', system-ui, sans-serif",
                }}>
                  Click again to confirm. This cannot be undone.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

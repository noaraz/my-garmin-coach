import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useGoogleOAuth } from '@react-oauth/google'
import { bootstrapAdmin, resetAdmins } from '../api/client'

export function SetupPage() {
  const [setupToken, setSetupToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [resetMsg, setResetMsg] = useState<string | null>(null)
  const { clientId, scriptLoadedSuccessfully } = useGoogleOAuth()

  const handleSignIn = () => {
    setError(null)
    if (!setupToken.trim()) {
      setError('Please enter your setup token first')
      return
    }
    if (!scriptLoadedSuccessfully) return
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const client = (window as any).google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: 'openid profile email',
      callback: async (response: { access_token?: string; error?: string }) => {
        if (response.error || !response.access_token) {
          setError('Google sign-in failed')
          return
        }
        try {
          await bootstrapAdmin(setupToken, response.access_token)
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
        }
      },
    })
    client.requestAccessToken()
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
                Sign in &rarr;
              </Link>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '20px' }}>
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

              {error && (
                <div
                  role="alert"
                  style={{
                    marginBottom: '14px',
                    padding: '9px 11px',
                    background: 'var(--bg-surface-2)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '5px',
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                  }}
                >
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <button
                  onClick={handleSignIn}
                  disabled={!scriptLoadedSuccessfully}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 20px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '4px',
                    fontSize: '14px',
                    fontWeight: 500,
                    color: 'var(--text-primary)',
                    cursor: scriptLoadedSuccessfully ? 'pointer' : 'not-allowed',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                    <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
                    <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
                    <path fill="#FBBC05" d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z"/>
                    <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
                  </svg>
                  Sign in with Google
                </button>
              </div>
            </div>
          )}

          {/* Danger zone -- always visible */}
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
                  background: 'var(--bg-surface-2)',
                  border: '1px solid var(--border)',
                  borderRadius: '5px',
                  fontSize: '12px',
                  color: 'var(--accent)',
                  fontFamily: "'Barlow', system-ui, sans-serif",
                }}>
                  {resetMsg}
                </div>
              )}

              <button
                type="button"
                onClick={() => { void handleReset() }}
                disabled={isResetting}
                style={{
                  padding: '8px 16px',
                  background: confirmReset ? 'var(--bg-surface-2)' : 'transparent',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-strong)',
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
                {isResetting ? 'Removing...' : confirmReset ? 'Confirm Remove All Admins' : 'Remove All Admins'}
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

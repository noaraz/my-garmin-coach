import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

/**
 * Handles the OAuth implicit flow redirect from Google.
 * Google redirects back to /auth/callback#access_token=...
 * We parse the token from the hash and exchange it via googleLogin().
 */
export function AuthCallbackPage() {
  const { googleLogin } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1))
    const accessToken = hash.get('access_token')
    const errorParam = hash.get('error')

    if (errorParam) {
      setError('Google sign-in was cancelled or failed')
      return
    }

    if (!accessToken) {
      // No token in hash — user may have navigated here directly
      navigate('/login', { replace: true })
      return
    }

    googleLogin(accessToken)
      .then(() => navigate('/calendar', { replace: true }))
      .catch(err => setError(err instanceof Error ? err.message : 'Login failed'))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-main)',
        gap: 16,
        padding: '0 24px',
      }}>
        <div style={{
          fontFamily: 'var(--font-family-display)',
          fontSize: 14,
          color: 'var(--color-zone-5)',
          textAlign: 'center',
        }}>{error}</div>
        <button
          onClick={() => navigate('/login', { replace: true })}
          style={{
            padding: '10px 20px',
            background: 'var(--accent)',
            color: 'var(--text-on-accent)',
            border: 'none',
            borderRadius: 6,
            fontFamily: 'var(--font-family-display)',
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >Try Again</button>
      </div>
    )
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
        fontFamily: 'var(--font-family-mono)',
        fontSize: 13,
        color: 'var(--text-muted)',
        letterSpacing: '0.05em',
      }}>Signing in…</div>
    </div>
  )
}

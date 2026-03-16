import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function LoginPage() {
  const { googleLogin } = useAuth()
  const navigate = useNavigate()

  const [idToken, setIdToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await googleLogin(idToken)
      navigate('/calendar')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsSubmitting(false)
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
          }}>Sign In</h1>

          <form onSubmit={handleSubmit} noValidate action="." method="post">
            <div style={{ marginBottom: '20px' }}>
              <label
                htmlFor="id-token"
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
                Google ID Token
              </label>
              <input
                id="id-token"
                name="id-token"
                type="text"
                autoComplete="off"
                value={idToken}
                onChange={e => setIdToken(e.target.value)}
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
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

      </div>
    </div>
  )
}

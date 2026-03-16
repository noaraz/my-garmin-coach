import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../contexts/AuthContext'

export function RegisterPage() {
  const { googleLogin } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const inviteCode = searchParams.get('invite') ?? ''
  const [error, setError] = useState<string | null>(null)

  const handleSuccess = async (credential: string) => {
    setError(null)
    try {
      await googleLogin(credential, inviteCode)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
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
            margin: '0 0 6px',
          }}>Request Access</h1>

          <p style={{
            fontSize: '13px',
            color: 'var(--text-secondary)',
            fontFamily: "'Barlow', system-ui, sans-serif",
            margin: '0 0 20px',
          }}>Sign in with Google to create your account</p>

          {inviteCode && (
            <p style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              fontFamily: "'Barlow', system-ui, sans-serif",
              margin: '0 0 14px',
            }}>
              Invite code: {inviteCode}
            </p>
          )}

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
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                if (credentialResponse.credential) {
                  void handleSuccess(credentialResponse.credential)
                }
              }}
              onError={() => setError('Google sign-in failed')}
            />
          </div>
        </div>

        <p style={{
          textAlign: 'center',
          marginTop: '16px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          fontFamily: "'Barlow', system-ui, sans-serif",
        }}>
          Already have an account?{' '}
          <Link
            to="/login"
            style={{
              color: 'var(--accent)',
              textDecoration: 'none',
              fontWeight: 500,
            }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

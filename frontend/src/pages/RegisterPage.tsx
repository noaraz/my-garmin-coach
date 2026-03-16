import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useGoogleOAuth } from '@react-oauth/google'
import { useAuth } from '../contexts/AuthContext'

export function RegisterPage() {
  const { googleLogin } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { clientId, scriptLoadedSuccessfully } = useGoogleOAuth()

  const inviteCode = searchParams.get('invite') ?? ''
  const [error, setError] = useState<string | null>(null)

  const handleSignIn = () => {
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
        setError(null)
        try {
          await googleLogin(response.access_token, inviteCode)
          navigate('/')
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Registration failed')
        }
      },
    })
    client.requestAccessToken()
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-main)' }}>
      <div style={{ width: '100%', maxWidth: '380px', padding: '0 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px', justifyContent: 'center' }}>
          <div style={{ width: '34px', height: '34px', background: 'var(--accent)', borderRadius: '7px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-on-accent)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div style={{ fontFamily: "'Barlow Condensed', system-ui, sans-serif", fontWeight: 700, fontSize: '20px', letterSpacing: '0.08em', color: 'var(--text-primary)', textTransform: 'uppercase' as const }}>GarminCoach</div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '28px 24px' }}>
          <h1 style={{ fontFamily: "'Barlow Condensed', system-ui, sans-serif", fontWeight: 700, fontSize: '20px', letterSpacing: '0.06em', textTransform: 'uppercase' as const, color: 'var(--text-primary)', margin: '0 0 6px' }}>Request Access</h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', fontFamily: "'Barlow', system-ui, sans-serif", margin: '0 0 20px' }}>Sign in with Google to create your account</p>

          {inviteCode && (
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'Barlow', system-ui, sans-serif", margin: '0 0 14px' }}>
              Invite code: {inviteCode}
            </p>
          )}

          {error && (
            <div role="alert" style={{ marginBottom: '14px', padding: '9px 11px', background: 'var(--bg-surface-2)', border: '1px solid var(--border-strong)', borderRadius: '5px', fontSize: '12px', color: 'var(--text-secondary)', fontFamily: "'Barlow', system-ui, sans-serif" }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button
              onClick={handleSignIn}
              disabled={!scriptLoadedSuccessfully}
              style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-strong)', borderRadius: '4px', fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)', cursor: scriptLoadedSuccessfully ? 'pointer' : 'not-allowed', fontFamily: "'Barlow', system-ui, sans-serif" }}
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

        <p style={{ textAlign: 'center', marginTop: '16px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: "'Barlow', system-ui, sans-serif" }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}

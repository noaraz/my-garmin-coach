import { useState, useEffect, type FormEvent } from 'react'
import { getGarminStatus, connectGarmin, disconnectGarmin, createInvite } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

type ConnectionState = 'loading' | 'connected' | 'disconnected'

const sectionLabel: React.CSSProperties = {
  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '0.15em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '12px',
}

export function SettingsPage() {
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading')
  const [garminEmail, setGarminEmail] = useState('')
  const [garminPassword, setGarminPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const { isAdmin } = useAuth()

  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    getGarminStatus()
      .then(res => setConnectionState(res.connected ? 'connected' : 'disconnected'))
      .catch(() => setConnectionState('disconnected'))
  }, [])

  const handleConnect = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccessMsg(null)
    setIsSubmitting(true)
    try {
      const res = await connectGarmin(garminEmail, garminPassword)
      if (res.connected) {
        setConnectionState('connected')
        setGarminEmail('')
        setGarminPassword('')
        setSuccessMsg('Garmin account connected successfully.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGenerateInvite = async () => {
    setInviteError(null)
    setInviteLink(null)
    setIsGenerating(true)
    try {
      const res = await createInvite()
      setInviteLink(`${window.location.origin}/register?invite=${res.code}`)
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : 'Failed to generate invite')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCopy = () => {
    if (inviteLink) {
      void navigator.clipboard.writeText(inviteLink)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDisconnect = async () => {
    setError(null)
    setSuccessMsg(null)
    setIsSubmitting(true)
    try {
      await disconnectGarmin()
      setConnectionState('disconnected')
      setSuccessMsg('Garmin account disconnected.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div style={{ padding: '28px 32px', maxWidth: '680px' }}>
      {/* Page header */}
      <h1 style={{
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        fontSize: '26px',
        fontWeight: 700,
        letterSpacing: '0.02em',
        color: 'var(--text-primary)',
        margin: '0 0 28px',
        lineHeight: 1.1,
        textTransform: 'uppercase',
      }}>
        Settings
      </h1>

      {/* Garmin Connect section */}
      <div>
        <div style={sectionLabel}>Garmin Connect</div>

        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '20px 22px',
        }}>
          {/* Status row — always visible */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: connectionState !== 'loading' ? '20px' : '0',
          }}>
            {connectionState === 'loading' ? (
              <span style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                fontFamily: "'Barlow', system-ui, sans-serif",
              }}>
                Checking connection…
              </span>
            ) : (
              <>
                {/* Coloured dot */}
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: connectionState === 'connected' ? 'var(--color-success)' : 'var(--color-error)',
                  flexShrink: 0,
                  boxShadow: connectionState === 'connected'
                    ? '0 0 0 3px var(--color-success-glow)'
                    : '0 0 0 3px var(--color-error-glow)',
                }} />
                <span style={{
                  fontSize: '13px',
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: connectionState === 'connected' ? 'var(--color-success)' : 'var(--text-secondary)',
                }}>
                  {connectionState === 'connected' ? 'Connected' : 'Not connected'}
                </span>
              </>
            )}
          </div>

          {/* Error / success messages */}
          {error && (
            <div style={{
              marginBottom: '14px',
              padding: '9px 11px',
              background: 'var(--color-error-bg)',
              border: '1px solid var(--color-error-border)',
              borderRadius: '5px',
              fontSize: '12px',
              color: 'var(--color-error)',
              fontFamily: "'Barlow', system-ui, sans-serif",
            }}>
              {error}
            </div>
          )}
          {successMsg && (
            <div style={{
              marginBottom: '14px',
              padding: '9px 11px',
              background: 'var(--color-success-bg)',
              border: '1px solid var(--color-success-border)',
              borderRadius: '5px',
              fontSize: '12px',
              color: 'var(--color-success)',
              fontFamily: "'Barlow', system-ui, sans-serif",
            }}>
              {successMsg}
            </div>
          )}

          {/* Not connected — connect form */}
          {connectionState === 'disconnected' && (
            <form onSubmit={handleConnect} noValidate action="." method="post">
              <p style={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                fontFamily: "'Barlow', system-ui, sans-serif",
                margin: '0 0 16px',
                lineHeight: 1.5,
              }}>
                Enter your Garmin Connect credentials to sync workouts. Your password is used once
                to obtain an OAuth token and is never stored.
              </p>

              <div style={{ marginBottom: '12px' }}>
                <label htmlFor="garmin-email" style={{
                  display: 'block',
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  marginBottom: '5px',
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                }}>
                  Garmin Email
                </label>
                <input
                  id="garmin-email"
                  name="username"
                  type="email"
                  autoComplete="username"
                  value={garminEmail}
                  onChange={e => setGarminEmail(e.target.value)}
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
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label htmlFor="garmin-password" style={{
                  display: 'block',
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  marginBottom: '5px',
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                }}>
                  Garmin Password
                </label>
                <input
                  id="garmin-password"
                  name="password"
                  type="password"
                  autoComplete="off"
                  value={garminPassword}
                  onChange={e => setGarminPassword(e.target.value)}
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
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !garminEmail || !garminPassword}
                style={{
                  padding: '9px 20px',
                  background: isSubmitting ? 'var(--border-strong)' : 'var(--accent)',
                  color: 'var(--text-on-accent)',
                  border: 'none',
                  borderRadius: '5px',
                  fontSize: '11px',
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {isSubmitting ? 'Connecting…' : 'Connect Garmin'}
              </button>
            </form>
          )}

          {/* Connected — show disconnect */}
          {connectionState === 'connected' && (
            <div>
              <p style={{
                fontSize: '12px',
                color: 'var(--text-secondary)',
                fontFamily: "'Barlow', system-ui, sans-serif",
                margin: '0 0 16px',
                lineHeight: 1.5,
              }}>
                Your Garmin account is linked. Workouts will sync automatically when you use the
                Sync All button on the calendar.
              </p>
              <button
                onClick={handleDisconnect}
                disabled={isSubmitting}
                style={{
                  padding: '8px 16px',
                  background: 'transparent',
                  color: 'var(--color-error)',
                  border: '1px solid var(--color-error-border-weak)',
                  borderRadius: '5px',
                  fontSize: '11px',
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  transition: 'border-color 0.15s, color 0.15s',
                }}
              >
                {isSubmitting ? 'Disconnecting…' : 'Disconnect'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Admin section — only visible to admin users */}
      {isAdmin && (
        <div style={{ marginTop: '32px' }}>
          <div style={sectionLabel}>Admin</div>

          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '20px 22px',
          }}>
            <p style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              fontFamily: "'Barlow', system-ui, sans-serif",
              margin: '0 0 16px',
              lineHeight: 1.5,
            }}>
              Generate a one-time invite link to share with a friend. Each link can only be used once.
            </p>

            {inviteError && (
              <div style={{
                marginBottom: '14px',
                padding: '9px 11px',
                background: 'var(--color-error-bg)',
                border: '1px solid var(--color-error-border)',
                borderRadius: '5px',
                fontSize: '12px',
                color: 'var(--color-error)',
                fontFamily: "'Barlow', system-ui, sans-serif",
              }}>
                {inviteError}
              </div>
            )}

            <button
              onClick={handleGenerateInvite}
              disabled={isGenerating}
              style={{
                padding: '9px 20px',
                background: isGenerating ? 'var(--border-strong)' : 'var(--accent)',
                color: 'var(--text-on-accent)',
                border: 'none',
                borderRadius: '5px',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase' as const,
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                cursor: isGenerating ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s',
              }}
            >
              {isGenerating ? 'Generating…' : 'Generate Invite Link'}
            </button>

            {inviteLink && (
              <div style={{ marginTop: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  readOnly
                  value={inviteLink}
                  style={{
                    flex: 1,
                    padding: '9px 11px',
                    background: 'var(--bg-surface-2)',
                    border: '1px solid var(--border)',
                    borderRadius: '5px',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                    fontFamily: "'Barlow', system-ui, sans-serif",
                    outline: 'none',
                    boxSizing: 'border-box' as const,
                  }}
                />
                <button
                  onClick={handleCopy}
                  style={{
                    padding: '9px 14px',
                    background: copied ? 'var(--color-success)' : 'var(--bg-surface-3)',
                    color: copied ? 'var(--text-on-accent)' : 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: '5px',
                    fontSize: '11px',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase' as const,
                    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                    cursor: 'pointer',
                    transition: 'background 0.15s, color 0.15s',
                    whiteSpace: 'nowrap' as const,
                    flexShrink: 0,
                  }}
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

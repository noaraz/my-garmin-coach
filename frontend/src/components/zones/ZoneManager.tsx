import { useState } from 'react'
import { useZones } from '../../hooks/useZones'
import { useProfile } from '../../hooks/useProfile'
import { useZonesStatus } from '../../contexts/ZonesStatusContext'
import { HRZoneTable } from './HRZoneTable'
import { PaceZoneTable } from './PaceZoneTable'
import { ThresholdInput } from './ThresholdInput'
import type { HRZone } from '../../api/types'

export function ZoneManager() {
  const { hrZones, paceZones, loading: zonesLoading, error: zonesError, saveHRZones, recalcHR, recalcPace } = useZones()
  const { profile, loading: profileLoading, error: profileError, save } = useProfile()
  const { refreshZones } = useZonesStatus()

  const [lthr, setLthr] = useState<number | null>(null)
  const [thresholdPace, setThresholdPace] = useState<number | null>(null)
  const [localZones, setLocalZones] = useState<HRZone[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Sync local state from profile when it loads
  const resolvedLthr = lthr !== null ? lthr : (profile?.lthr ?? null)
  const resolvedThresholdPace = thresholdPace !== null ? thresholdPace : (profile?.threshold_pace ?? null)
  const displayZones = localZones.length > 0 ? localZones : hrZones

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSave = async () => {
    try {
      await save({
        lthr: resolvedLthr ?? undefined,
        threshold_pace: resolvedThresholdPace ?? undefined,
      })
      if (localZones.length > 0) {
        await saveHRZones(localZones)
        setLocalZones([])
      }
      showToast('success', 'Saved successfully')
      refreshZones()
    } catch (e) {
      showToast('error', e instanceof Error ? e.message : 'Save failed')
    }
  }

  const handleRecalcHR = async () => {
    try {
      await recalcHR()
      setLocalZones([])
      showToast('success', 'HR zones recalculated')
    } catch (e) {
      showToast('error', e instanceof Error ? e.message : 'Recalculation failed')
    }
  }

  const handleRecalcPace = async () => {
    try {
      await recalcPace()
      showToast('success', 'Pace zones recalculated')
    } catch (e) {
      showToast('error', e instanceof Error ? e.message : 'Recalculation failed')
    }
  }

  const handleZoneChange = (zoneNumber: number, field: 'lower_bpm' | 'upper_bpm', value: number) => {
    const base = localZones.length > 0 ? localZones : hrZones
    setLocalZones(base.map(z =>
      z.zone_number === zoneNumber ? { ...z, [field]: value } : z
    ))
  }

  const sectionLabel: React.CSSProperties = {
    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.15em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    marginBottom: '10px',
  }

  if (zonesLoading || profileLoading) {
    return (
      <div style={{ padding: '40px', fontFamily: "'IBM Plex Mono', monospace", fontSize: '12px', color: 'var(--text-muted)' }}>
        Loading zones…
      </div>
    )
  }

  const error = zonesError || profileError

  return (
    <div style={{ padding: '28px 32px', maxWidth: '900px' }}>
      {/* Page header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '26px',
          fontWeight: 700,
          letterSpacing: '0.02em',
          color: 'var(--text-primary)',
          margin: 0,
          lineHeight: 1.1,
        }}>Zone Manager</h1>
        <div style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '9px',
          color: 'var(--text-muted)',
          marginTop: '4px',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>Configure Training Zones</div>
      </div>

      {error && (
        <div role="alert" style={{
          background: 'var(--color-error-bg)', border: '1px solid var(--color-error-border)',
          color: 'var(--color-error)', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{error}</div>
      )}
      {toast?.type === 'error' && (
        <div role="alert" style={{
          background: 'var(--color-error-bg)', border: '1px solid var(--color-error-border)',
          color: 'var(--color-error)', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{toast.message}</div>
      )}
      {toast?.type === 'success' && (
        <div role="status" style={{
          background: 'var(--color-success-bg)', border: '1px solid var(--color-success-border)',
          color: 'var(--color-success)', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{toast.message}</div>
      )}

      {/* Thresholds */}
      <section style={{ marginBottom: '28px' }}>
        <div style={sectionLabel}>Thresholds</div>
        {/* Guide card */}
        <div style={{
          background: 'var(--accent-subtle)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '16px 18px',
          marginBottom: '12px',
        }}>
          <div style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '12px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            How to find your thresholds
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <div style={{ fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif", fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                LTHR — Lactate Threshold HR
              </div>
              <div style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: '5px' }}>
                Run 30 min all-out. Your LTHR ≈ average HR during the last 20 min.
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--accent)', fontWeight: 500 }}>or: </span>
                average HR from a recent 10K race
              </div>
            </div>
            <div>
              <div style={{ fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif", fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                Threshold Pace
              </div>
              <div style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: '5px' }}>
                Best average pace for a 30-min all-out time trial.
              </div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--accent)', fontWeight: 500 }}>or: </span>
                your recent 10K race pace (±5 sec/km)
              </div>
            </div>
          </div>
          <div style={{
            marginTop: '12px',
            paddingTop: '10px',
            borderTop: '1px solid var(--border)',
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-secondary)',
          }}>
            Zones are calculated using the{' '}
            <a
              href="https://www.joefrielsblog.com/"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}
            >
              Friel method ↗
            </a>
          </div>
        </div>
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px', padding: '16px 20px' }}>
          <ThresholdInput
            lthr={resolvedLthr}
            thresholdPace={resolvedThresholdPace}
            onLthrChange={val => setLthr(val)}
            onThresholdPaceChange={val => setThresholdPace(val)}
            onSave={handleSave}
          />
        </div>
      </section>

      {/* HR Zones */}
      <section style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={sectionLabel}>Heart Rate Zones</div>
          <button
            onClick={handleRecalcHR}
            style={{
              padding: '5px 12px',
              background: 'transparent',
              border: '1px solid var(--border-strong)',
              borderRadius: '4px',
              fontSize: '10px',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Recalculate
          </button>
        </div>
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px', overflow: 'hidden' }}>
          <HRZoneTable zones={displayZones} onZoneChange={handleZoneChange} />
        </div>
      </section>

      {/* Pace Zones */}
      <section>
        <div style={sectionLabel}>Pace Zones</div>
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px', overflow: 'hidden' }}>
          <PaceZoneTable zones={paceZones} onRecalculate={handleRecalcPace} />
        </div>
      </section>
    </div>
  )
}

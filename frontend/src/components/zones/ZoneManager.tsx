import { useState } from 'react'
import { useZones } from '../../hooks/useZones'
import { useProfile } from '../../hooks/useProfile'
import { HRZoneTable } from './HRZoneTable'
import { PaceZoneTable } from './PaceZoneTable'
import { ThresholdInput } from './ThresholdInput'
import { MethodSelector } from './MethodSelector'
import type { HRZone } from '../../api/types'

export function ZoneManager() {
  const { hrZones, paceZones, loading: zonesLoading, error: zonesError, recalcHR, recalcPace } = useZones()
  const { profile, loading: profileLoading, error: profileError, save } = useProfile()

  const [lthr, setLthr] = useState<number | null>(null)
  const [thresholdPace, setThresholdPace] = useState<number | null>(null)
  const [method, setMethod] = useState('coggan')
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
      showToast('success', 'Saved successfully')
    } catch (e) {
      showToast('error', e instanceof Error ? e.message : 'Save failed')
    }
  }

  const handleRecalcHR = async () => {
    try {
      await recalcHR()
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
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.15em',
    textTransform: 'uppercase',
    color: '#aaa',
    marginBottom: '10px',
  }

  if (zonesLoading || profileLoading) {
    return (
      <div style={{ padding: '40px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#aaa' }}>
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
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '26px',
          fontWeight: 700,
          letterSpacing: '0.02em',
          color: 'var(--text-primary)',
          margin: 0,
          lineHeight: 1.1,
        }}>Zone Manager</h1>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '9px',
          color: '#bbb',
          marginTop: '4px',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>Configure Training Zones</div>
      </div>

      {error && (
        <div role="alert" style={{
          background: '#fff0f0', border: '1px solid #ffc5c5',
          color: '#c00', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{error}</div>
      )}
      {toast?.type === 'error' && (
        <div role="alert" style={{
          background: '#fff0f0', border: '1px solid #ffc5c5',
          color: '#c00', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{toast.message}</div>
      )}
      {toast?.type === 'success' && (
        <div role="status" style={{
          background: '#f0fff4', border: '1px solid #b2f5c8',
          color: '#0a7a30', padding: '10px 14px', borderRadius: '5px',
          fontSize: '13px', marginBottom: '20px',
        }}>{toast.message}</div>
      )}

      {/* Thresholds */}
      <section style={{ marginBottom: '28px' }}>
        <div style={sectionLabel}>Thresholds</div>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MethodSelector value={method} onChange={setMethod} />
            <button
              onClick={handleRecalcHR}
              style={{
                padding: '5px 12px',
                background: 'transparent',
                border: '1px solid var(--border-strong)',
                borderRadius: '4px',
                fontSize: '10px',
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
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

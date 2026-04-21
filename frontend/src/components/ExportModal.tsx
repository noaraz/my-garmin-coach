import { useState, useEffect } from 'react'
import { DayPicker, type DateRange } from 'react-day-picker'
import 'react-day-picker/dist/style.css'
import { exportActivities } from '../api/client'

interface Props {
  isOpen: boolean
  onClose: () => void
}

type ExportState = 'idle' | 'loading' | 'error'

export default function ExportModal({ isOpen, onClose }: Props) {
  // Default: last 30 days (local midnight)
  const today = new Date()
  const thirtyDaysAgo = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)

  const [range, setRange] = useState<DateRange | undefined>({
    from: thirtyDaysAgo,
    to: today,
  })
  const [state, setState] = useState<ExportState>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleDownload = async () => {
    if (!range?.from || !range?.to) return
    setState('loading')
    setErrorMsg('')
    try {
      const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
      await exportActivities(fmt(range.from), fmt(range.to))
      setState('idle')
      onClose()
    } catch (err) {
      setState('error')
      setErrorMsg(err instanceof Error ? err.message : 'Export failed')
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 24,
          maxWidth: 380,
          width: '100%',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ fontFamily: 'var(--font-family-display)', fontSize: 16, color: 'var(--text-primary)' }}>
            Export Activity Data
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              fontSize: 18,
            }}
          >
            ✕
          </button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16 }}>
          Downloads a JSON file with full lap data for all activities in the selected range.
        </p>

        <DayPicker
          mode="range"
          selected={range}
          onSelect={setRange}
          numberOfMonths={1}
        />

        {state === 'error' && (
          <p style={{ color: 'var(--text-primary)', fontSize: 12, marginTop: 8 }}>{errorMsg}</p>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button
            onClick={onClose}
            aria-label="Cancel"
            style={{
              flex: 1,
              padding: '8px 0',
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--bg-surface-2)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleDownload}
            disabled={state === 'loading' || !range?.from || !range?.to}
            aria-label="Download JSON"
            style={{
              flex: 1,
              padding: '8px 0',
              borderRadius: 8,
              border: 'none',
              background: 'var(--accent)',
              color: 'var(--text-on-accent)',
              cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              opacity: state === 'loading' ? 0.7 : 1,
            }}
          >
            {state === 'loading' ? 'Fetching from Garmin…' : '↓ Download JSON'}
          </button>
        </div>
      </div>
    </div>
  )
}

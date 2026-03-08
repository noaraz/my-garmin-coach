import { useState } from 'react'
import { scheduleWorkout } from '../../api/client'
import type { WorkoutTemplate } from '../../api/types'

interface ScheduleDialogProps {
  template: WorkoutTemplate
  onClose: () => void
  onScheduled?: () => void
}

export function ScheduleDialog({ template, onClose, onScheduled }: ScheduleDialogProps) {
  const [date, setDate] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSchedule = async () => {
    if (!date) return
    setLoading(true)
    try {
      await scheduleWorkout({ template_id: template.id, date })
      onScheduled?.()
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const labelStyle: React.CSSProperties = {
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    display: 'block',
    marginBottom: '4px',
  }

  const inputStyle: React.CSSProperties = {
    display: 'block',
    width: '100%',
    padding: '6px 10px',
    background: 'var(--input-bg)',
    border: '1px solid var(--input-border)',
    borderRadius: '3px',
    color: 'var(--text-primary)',
    fontFamily: "'Barlow', system-ui, sans-serif",
    fontSize: '13px',
    outline: 'none',
  }

  return (
    <div
      role="dialog"
      aria-label="Schedule"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: '6px',
          padding: '24px',
          minWidth: '320px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        }}
      >
        <h2 style={{
          margin: 0,
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '16px',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--text-primary)',
        }}>
          Schedule Workout
          <div style={{
            fontFamily: "'Barlow', system-ui, sans-serif",
            fontSize: '13px',
            fontWeight: 400,
            letterSpacing: 0,
            textTransform: 'none',
            color: 'var(--text-secondary)',
            marginTop: '4px',
          }}>
            {template.name}
          </div>
        </h2>

        <div>
          <label htmlFor="dialog-schedule-date" style={labelStyle}>Date</label>
          <input
            id="dialog-schedule-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '6px 16px',
              cursor: 'pointer',
              fontFamily: "'Barlow Condensed', system-ui, sans-serif",
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              background: 'transparent',
              border: '1px solid var(--border-strong)',
              borderRadius: '3px',
              color: 'var(--text-secondary)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSchedule}
            disabled={!date || loading}
            style={{
              padding: '6px 16px',
              cursor: date && !loading ? 'pointer' : 'not-allowed',
              fontFamily: "'Barlow Condensed', system-ui, sans-serif",
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              background: date && !loading ? '#0057ff' : 'var(--bg-surface-3)',
              border: '1px solid transparent',
              borderRadius: '3px',
              color: date && !loading ? '#ffffff' : 'var(--text-muted)',
              transition: 'background 0.1s',
            }}
          >
            {loading ? 'Scheduling...' : 'Schedule'}
          </button>
        </div>
      </div>
    </div>
  )
}

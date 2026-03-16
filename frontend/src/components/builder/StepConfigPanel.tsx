import { useState, useEffect } from 'react'
import type { BuilderStep, WorkoutStep, RepeatGroup } from '../../api/types'
import { DurationTimeInput, DurationDistanceInput } from './DurationInput'
import { ZoneSelector } from './ZoneSelector'

interface StepConfigPanelProps {
  step: BuilderStep
  onChange: (step: BuilderStep) => void
}

function isRepeatGroup(step: BuilderStep): step is RepeatGroup {
  return step.type === 'repeat'
}

const fieldLabel: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '4px',
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  padding: '5px 8px',
  marginTop: '4px',
  fontSize: '12px',
  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
  background: 'var(--input-bg)',
  border: '1px solid var(--input-border)',
  borderRadius: '3px',
  color: 'var(--text-primary)',
  outline: 'none',
}

function RepeatGroupPanel({ step, onChange }: { step: RepeatGroup; onChange: (s: BuilderStep) => void }) {
  const [count, setCount] = useState(step.repeat_count.toString())

  useEffect(() => {
    setCount(step.repeat_count.toString())
  }, [step.repeat_count])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div>
        <div style={fieldLabel}>Repeat Count</div>
        <input
          id="repeat-count-input"
          aria-label="repeat"
          type="number"
          min={1}
          value={count}
          onChange={(e) => setCount(e.target.value)}
          onBlur={() => onChange({ ...step, repeat_count: parseInt(count, 10) || 1 })}
          style={{ ...inputStyle, width: '80px' }}
        />
      </div>
    </div>
  )
}

function WorkoutStepPanel({ step, onChange }: { step: WorkoutStep; onChange: (s: BuilderStep) => void }) {
  const [notes, setNotes] = useState(step.notes ?? '')

  useEffect(() => {
    setNotes(step.notes ?? '')
  }, [step.notes, step.id])

  const handleDurationTypeToggle = (type: 'time' | 'distance') => {
    onChange({ ...step, duration_type: type })
  }

  const handleTargetTypeChange = (value: string) => {
    onChange({ ...step, target_type: value as WorkoutStep['target_type'] })
  }

  const handleZoneChange = (zone: number) => {
    onChange({ ...step, zone })
  }

  const handleTimeChange = (seconds: number) => {
    onChange({ ...step, duration_sec: seconds })
  }

  const handleDistanceChange = (distanceM: number) => {
    onChange({ ...step, distance_m: distanceM })
  }

  const handleNotesBlur = () => {
    onChange({ ...step, notes })
  }

  const toggleBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '4px 12px',
    cursor: 'pointer',
    borderRadius: '3px',
    fontSize: '10px',
    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    border: '1px solid var(--border-strong)',
    background: active ? 'var(--text-primary)' : 'transparent',
    color: active ? 'var(--bg-surface)' : 'var(--text-secondary)',
    transition: 'background 0.1s, color 0.1s',
  })

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
      {/* Duration type toggle */}
      <div>
        <div style={fieldLabel}>Duration Type</div>
        <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
          <button onClick={() => handleDurationTypeToggle('time')} style={toggleBtnStyle(step.duration_type === 'time')}>
            Time
          </button>
          <button onClick={() => handleDurationTypeToggle('distance')} style={toggleBtnStyle(step.duration_type === 'distance')}>
            Distance
          </button>
        </div>
      </div>

      {/* Duration/Distance input */}
      <div>
        {step.duration_type === 'time' ? (
          <DurationTimeInput seconds={step.duration_sec ?? 0} onChange={handleTimeChange} label="Duration" />
        ) : (
          <DurationDistanceInput distanceM={step.distance_m ?? 0} onChange={handleDistanceChange} label="Distance" />
        )}
      </div>

      {/* Target type */}
      <div>
        <div style={fieldLabel}>Target</div>
        <select
          id="target-select"
          aria-label="target"
          value={step.target_type}
          onChange={(e) => handleTargetTypeChange(e.target.value)}
          style={{ ...inputStyle, marginTop: '4px', width: '100%' }}
        >
          <option value="hr_zone">HR Zone</option>
          <option value="pace_zone">Pace Zone</option>
          <option value="open">Open</option>
        </select>
      </div>

      {/* Zone selector */}
      {(step.target_type === 'hr_zone' || step.target_type === 'pace_zone') ? (
        <ZoneSelector zone={step.zone} onChange={handleZoneChange} />
      ) : <div />}

      {/* Notes — spans full width */}
      <div style={{ gridColumn: '1 / -1' }}>
        <div style={fieldLabel}>Notes</div>
        <textarea
          id="notes-input"
          aria-label="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleNotesBlur}
          style={{
            ...inputStyle,
            width: '100%',
            minHeight: '52px',
            resize: 'vertical',
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '12px',
          }}
        />
      </div>
    </div>
  )
}

export function StepConfigPanel({ step, onChange }: StepConfigPanelProps) {
  if (isRepeatGroup(step)) {
    return <RepeatGroupPanel step={step} onChange={onChange} />
  }
  return <WorkoutStepPanel step={step} onChange={onChange} />
}

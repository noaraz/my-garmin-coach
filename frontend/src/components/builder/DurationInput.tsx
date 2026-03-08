import { useState, useEffect } from 'react'

const fieldLabel: React.CSSProperties = {
  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  padding: '5px 8px',
  marginTop: '4px',
  fontSize: '12px',
  fontFamily: "'JetBrains Mono', monospace",
  background: 'var(--input-bg)',
  border: '1px solid var(--input-border)',
  borderRadius: '3px',
  color: 'var(--text-primary)',
  outline: 'none',
  width: '100px',
}

interface TimeInputProps {
  seconds: number
  onChange: (seconds: number) => void
  label?: string
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function parseTime(value: string): number {
  if (value.includes(':')) {
    const [mins, secs] = value.split(':').map(Number)
    return (mins || 0) * 60 + (secs || 0)
  }
  return parseInt(value, 10) * 60 || 0
}

export function DurationTimeInput({ seconds, onChange, label = 'Duration' }: TimeInputProps) {
  const [raw, setRaw] = useState(formatTime(seconds))

  useEffect(() => {
    setRaw(formatTime(seconds))
  }, [seconds])

  return (
    <div>
      <div style={fieldLabel}>{label}</div>
      <input
        id="duration-input"
        aria-label={label}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onBlur={() => onChange(parseTime(raw))}
        placeholder="5:00"
        style={inputStyle}
      />
    </div>
  )
}

interface DistanceInputProps {
  distanceM: number
  onChange: (distanceM: number) => void
  label?: string
}

export function DurationDistanceInput({ distanceM, onChange, label = 'Distance' }: DistanceInputProps) {
  const [raw, setRaw] = useState((distanceM / 1000).toString())

  useEffect(() => {
    setRaw((distanceM / 1000).toString())
  }, [distanceM])

  return (
    <div>
      <div style={fieldLabel}>{label} (km)</div>
      <input
        id="distance-input"
        aria-label={label}
        type="number"
        step="0.1"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onBlur={() => onChange(Math.round(parseFloat(raw) * 1000))}
        style={inputStyle}
      />
    </div>
  )
}

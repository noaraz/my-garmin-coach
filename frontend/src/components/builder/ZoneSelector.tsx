import { ZONE_COLORS } from '../../utils/colors'

interface ZoneSelectorProps {
  zone: number | undefined
  onChange: (zone: number) => void
}

const ZONE_NAMES = ['Recovery', 'Aerobic', 'Tempo', 'Threshold', 'VO2max']

const fieldLabel: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

export function ZoneSelector({ zone, onChange }: ZoneSelectorProps) {
  return (
    <div>
      <div style={fieldLabel}>Zone</div>
      <select
        id="zone-select"
        aria-label="zone"
        value={zone ?? 1}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        style={{
          display: 'block',
          padding: '5px 8px',
          marginTop: '4px',
          fontSize: '12px',
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          background: 'var(--input-bg)',
          border: `1px solid ${zone ? ZONE_COLORS[zone] : 'var(--input-border)'}`,
          borderRadius: '3px',
          color: zone ? ZONE_COLORS[zone] : 'var(--text-primary)',
          outline: 'none',
          width: '100%',
          fontWeight: 600,
        }}
      >
        {[1, 2, 3, 4, 5].map(z => (
          <option key={z} value={z}>
            Zone {z} — {ZONE_NAMES[z - 1]}
          </option>
        ))}
      </select>
    </div>
  )
}

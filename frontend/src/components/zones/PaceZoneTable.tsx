import type { PaceZone } from '../../api/types'
import { formatPace } from '../../utils/formatting'

interface PaceZoneTableProps {
  zones: PaceZone[]
  onRecalculate: () => void
}

const ZONE_COLORS: Record<number, string> = {
  1: 'var(--color-zone-1)',
  2: 'var(--color-zone-2)',
  3: 'var(--color-zone-3)',
  4: 'var(--color-zone-4)',
  5: 'var(--color-zone-5)',
}

export function PaceZoneTable({ zones, onRecalculate }: PaceZoneTableProps) {
  const thStyle: React.CSSProperties = {
    padding: '6px 10px',
    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    textAlign: 'left',
    background: 'var(--bg-surface-2)',
    borderBottom: '1px solid var(--border)',
  }

  const tdStyle: React.CSSProperties = {
    padding: '8px 10px',
    fontSize: '12px',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border)',
  }

  return (
    <div>
      <table data-testid="pace-zone-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thStyle}>Zone</th>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>Pace Range</th>
          </tr>
        </thead>
        <tbody>
          {zones.map(zone => (
            <tr key={zone.id}>
              <td style={{ ...tdStyle, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700, color: ZONE_COLORS[zone.zone_number] ?? 'var(--text-muted)' }}>
                Z{zone.zone_number}
              </td>
              <td style={tdStyle}>{zone.name}</td>
              <td style={{ ...tdStyle, fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px' }}>
                {formatPace(zone.upper_pace)} – {formatPace(zone.lower_pace)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={onRecalculate}
          style={{
            padding: '5px 14px',
            background: 'transparent',
            border: '1px solid var(--border-strong)',
            borderRadius: '3px',
            color: 'var(--text-secondary)',
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          Update from Threshold
        </button>
      </div>
    </div>
  )
}

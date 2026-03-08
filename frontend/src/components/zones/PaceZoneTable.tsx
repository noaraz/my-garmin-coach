import type { PaceZone } from '../../api/types'
import { formatPace } from '../../utils/formatting'

interface PaceZoneTableProps {
  zones: PaceZone[]
  onRecalculate: () => void
}

const ZONE_COLORS: Record<number, string> = {
  1: '#3B82F6',
  2: '#22C55E',
  3: '#EAB308',
  4: '#F97316',
  5: '#EF4444',
}

export function PaceZoneTable({ zones, onRecalculate }: PaceZoneTableProps) {
  const thStyle: React.CSSProperties = {
    padding: '6px 10px',
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
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
            <th style={thStyle}>Method</th>
          </tr>
        </thead>
        <tbody>
          {zones.map(zone => (
            <tr key={zone.id}>
              <td style={{ ...tdStyle, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: ZONE_COLORS[zone.zone_number] ?? 'var(--text-muted)' }}>
                Z{zone.zone_number}
              </td>
              <td style={tdStyle}>{zone.name}</td>
              <td style={{ ...tdStyle, fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
                {formatPace(zone.upper_pace)} – {formatPace(zone.lower_pace)}
              </td>
              <td style={{ ...tdStyle, color: 'var(--text-muted)', fontSize: '11px' }}>{zone.calculation_method}</td>
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
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
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

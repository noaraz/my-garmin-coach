import type { HRZone } from '../../api/types'

interface HRZoneTableProps {
  zones: HRZone[]
}

export function HRZoneTable({ zones }: HRZoneTableProps) {
  const zoneHex = (zoneNumber: number): string => {
    const colors: Record<number, string> = {
      1: '#3B82F6',
      2: '#22C55E',
      3: '#EAB308',
      4: '#F97316',
      5: '#EF4444',
    }
    return colors[zoneNumber] ?? '#9ca3af'
  }

  const thStyle: React.CSSProperties = {
    padding: '8px 12px',
    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
    textAlign: 'left',
    background: 'var(--bg-surface-2)',
    borderBottom: '1px solid var(--border)',
  }

  const tdStyle: React.CSSProperties = {
    padding: '9px 12px',
    borderBottom: '1px solid var(--border)',
  }

  return (
    <table data-testid="hr-zone-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
      <thead>
        <tr>
          <th style={thStyle}>Zone</th>
          <th style={thStyle}>Name</th>
          <th style={thStyle}>Lower BPM</th>
          <th style={thStyle}>Upper BPM</th>
        </tr>
      </thead>
      <tbody>
        {zones.map(zone => (
          <tr key={zone.id} style={{ transition: 'background 0.08s' }}>
            <td style={tdStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <div style={{
                  width: '4px',
                  height: '18px',
                  borderRadius: '2px',
                  background: zoneHex(zone.zone_number),
                  flexShrink: 0,
                }} />
                <span style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 500,
                  color: zoneHex(zone.zone_number),
                  letterSpacing: '0.03em',
                }}>Z{zone.zone_number}</span>
              </div>
            </td>
            <td style={{ ...tdStyle, fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', color: 'var(--text-primary)' }}>
              {zone.name}
            </td>
            <td style={tdStyle}>
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '12px',
                color: 'var(--text-secondary)',
              }}>{zone.lower_bpm}</span>
            </td>
            <td style={tdStyle}>
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '12px',
                color: 'var(--text-secondary)',
              }}>{zone.upper_bpm}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

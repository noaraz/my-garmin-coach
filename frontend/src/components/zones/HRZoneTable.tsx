import { useState } from 'react'
import type { HRZone } from '../../api/types'

interface HRZoneTableProps {
  zones: HRZone[]
  onZoneChange: (zoneNumber: number, field: 'lower_bpm' | 'upper_bpm', value: number) => void
}

export function HRZoneTable({ zones, onZoneChange }: HRZoneTableProps) {
  const [editingCell, setEditingCell] = useState<{ zoneNumber: number; field: 'lower_bpm' | 'upper_bpm' } | null>(null)

  const handleCellClick = (zoneNumber: number, field: 'lower_bpm' | 'upper_bpm') => {
    setEditingCell({ zoneNumber, field })
  }

  const handleInputBlur = () => {
    setEditingCell(null)
  }

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
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
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
            {/* Zone indicator */}
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
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 500,
                  color: zoneHex(zone.zone_number),
                  letterSpacing: '0.03em',
                }}>Z{zone.zone_number}</span>
              </div>
            </td>
            <td style={{ ...tdStyle, fontFamily: "'Barlow', system-ui, sans-serif", fontSize: '13px', color: 'var(--text-primary)' }}>
              {zone.name}
            </td>
            <td style={tdStyle}>
              {editingCell?.zoneNumber === zone.zone_number && editingCell.field === 'lower_bpm' ? (
                <input
                  type="number"
                  aria-label="lower bpm"
                  defaultValue={zone.lower_bpm}
                  onBlur={e => {
                    onZoneChange(zone.zone_number, 'lower_bpm', Number(e.target.value))
                    handleInputBlur()
                  }}
                  autoFocus
                  style={{
                    width: '72px',
                    border: '1px solid #0057ff',
                    borderRadius: '3px',
                    padding: '3px 6px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    outline: 'none',
                  }}
                />
              ) : (
                <span
                  data-testid={`hr-lower-bpm-${zone.zone_number}`}
                  onClick={() => handleCellClick(zone.zone_number, 'lower_bpm')}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '2px 4px',
                    borderRadius: '3px',
                    display: 'inline-block',
                  }}
                >{zone.lower_bpm}</span>
              )}
            </td>
            <td style={tdStyle}>
              {editingCell?.zoneNumber === zone.zone_number && editingCell.field === 'upper_bpm' ? (
                <input
                  type="number"
                  aria-label="upper bpm"
                  defaultValue={zone.upper_bpm}
                  onBlur={e => {
                    onZoneChange(zone.zone_number, 'upper_bpm', Number(e.target.value))
                    handleInputBlur()
                  }}
                  autoFocus
                  style={{
                    width: '72px',
                    border: '1px solid #0057ff',
                    borderRadius: '3px',
                    padding: '3px 6px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    outline: 'none',
                  }}
                />
              ) : (
                <span
                  data-testid={`hr-upper-bpm-${zone.zone_number}`}
                  onClick={() => handleCellClick(zone.zone_number, 'upper_bpm')}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '2px 4px',
                    borderRadius: '3px',
                    display: 'inline-block',
                  }}
                >{zone.upper_bpm}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

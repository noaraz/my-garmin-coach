import type { ValidateRow } from '../../api/types'

interface ValidationTableProps {
  rows: ValidateRow[]
}

const th: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '10px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  padding: '6px 10px',
  textAlign: 'left',
  borderBottom: '1px solid var(--border)',
  whiteSpace: 'nowrap',
}

const td: React.CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '11px',
  color: 'var(--text-secondary)',
  padding: '6px 10px',
  borderBottom: '1px solid var(--border)',
  verticalAlign: 'top',
}

export function ValidationTable({ rows }: ValidationTableProps) {
  const allValid = rows.every(r => r.valid)

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: '6px',
      overflow: 'hidden',
      marginBottom: '16px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: 'var(--bg-surface-2)',
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 700,
          fontSize: '11px',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
        }}>
          {rows.length} workout{rows.length !== 1 ? 's' : ''}
        </span>
        <span style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '10px',
          color: allValid ? 'var(--color-success)' : 'var(--color-error)',
          fontWeight: 600,
        }}>
          {allValid ? '✓ All valid' : `${rows.filter(r => !r.valid).length} error${rows.filter(r => !r.valid).length > 1 ? 's' : ''}`}
        </span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={th}>#</th>
            <th style={th}>Date</th>
            <th style={th}>Name</th>
            <th style={th}>Steps</th>
            <th style={{ ...th, textAlign: 'center' }}>OK</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.row} style={{ background: row.valid ? 'transparent' : 'var(--color-error-bg)' }}>
              <td style={{ ...td, color: 'var(--text-muted)' }}>{row.row}</td>
              <td style={td}>{row.date}</td>
              <td style={{ ...td, color: 'var(--text-primary)', fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontWeight: 500 }}>
                {row.name}
              </td>
              <td style={td}>
                <span>{row.steps_spec}</span>
                {row.error && (
                  <div style={{ color: 'var(--color-error)', fontSize: '10px', marginTop: '3px' }}>
                    {row.error}
                  </div>
                )}
              </td>
              <td style={{ ...td, textAlign: 'center', color: row.valid ? 'var(--color-success)' : 'var(--color-error)', fontSize: '14px' }}>
                {row.valid ? '✓' : '✗'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

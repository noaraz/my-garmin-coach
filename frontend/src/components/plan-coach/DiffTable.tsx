import type { DiffResult, WorkoutDiff } from '../../api/types'

interface DiffTableProps {
  diff: DiffResult
}

function DiffRow({ item, kind }: { item: WorkoutDiff; kind: 'added' | 'removed' | 'changed' }) {
  const colors = {
    added: { bg: 'var(--color-success-bg)', text: 'var(--color-success)', symbol: '+' },
    removed: { bg: 'var(--color-error-bg)', text: 'var(--color-error)', symbol: '−' },
    changed: { bg: 'var(--color-warning-bg)', text: 'var(--color-warning)', symbol: '~' },
  }
  const c = colors[kind]
  return (
    <tr style={{ background: c.bg }}>
      <td style={{
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: '12px',
        fontWeight: 700,
        color: c.text,
        padding: '5px 10px 5px 12px',
        width: '28px',
      }}>
        {c.symbol}
      </td>
      <td style={{
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: '11px',
        color: 'var(--text-muted)',
        padding: '5px 10px',
        whiteSpace: 'nowrap',
      }}>
        {item.date}
      </td>
      <td style={{
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
        fontSize: '12px',
        color: 'var(--text-primary)',
        padding: '5px 10px 5px 0',
      }}>
        {item.name}
      </td>
    </tr>
  )
}

export function DiffTable({ diff }: DiffTableProps) {
  const totalAdded = diff.added.length
  const totalRemoved = diff.removed.length
  const totalChanged = diff.changed.length
  const hasChanges = totalAdded + totalRemoved + totalChanged > 0

  if (!hasChanges) return null

  return (
    <div
      data-testid="diff-table"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '5px',
        overflow: 'hidden',
        marginBottom: '16px',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '8px 12px',
        background: 'var(--bg-surface-2)',
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 700,
          fontSize: '10px',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
        }}>
          Changes vs current plan
        </span>
        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
          {totalAdded > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-success)' }}>
              +{totalAdded} added
            </span>
          )}
          {totalRemoved > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-error)' }}>
              −{totalRemoved} removed
            </span>
          )}
          {totalChanged > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--color-warning)' }}>
              ~{totalChanged} changed
            </span>
          )}
        </div>
      </div>

      {/* Rows */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {diff.added.map((item, i) => (
            <DiffRow key={`added-${i}`} item={item} kind="added" />
          ))}
          {diff.removed.map((item, i) => (
            <DiffRow key={`removed-${i}`} item={item} kind="removed" />
          ))}
          {diff.changed.map((item, i) => (
            <DiffRow key={`changed-${i}`} item={item} kind="changed" />
          ))}
        </tbody>
      </table>
    </div>
  )
}

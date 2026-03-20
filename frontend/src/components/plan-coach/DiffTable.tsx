import type { DiffResult, WorkoutDiff } from '../../api/types'

interface DiffTableProps {
  diff: DiffResult
}

type RowKind = 'added' | 'removed' | 'changed' | 'unchanged' | 'completed_locked'

const ROW_CONFIG: Record<RowKind, { symbol: string; color: string; bgVar: string }> = {
  added:            { symbol: '+',  color: 'var(--color-success)',  bgVar: 'var(--color-success-bg)' },
  removed:          { symbol: '−',  color: 'var(--color-error)',    bgVar: 'var(--color-error-bg)' },
  changed:          { symbol: '~',  color: 'var(--color-warning)',  bgVar: 'var(--color-warning-bg)' },
  unchanged:        { symbol: '=',  color: 'var(--text-muted)',     bgVar: 'transparent' },
  completed_locked: { symbol: '⊘',  color: 'var(--text-muted)',     bgVar: 'transparent' },
}

function DiffRow({ item, kind }: { item: WorkoutDiff; kind: RowKind }) {
  const c = ROW_CONFIG[kind]
  const isChanged = kind === 'changed' && (item.old_steps_spec || item.new_steps_spec)
  const isLocked = kind === 'completed_locked'
  const nameChanged = isChanged && item.old_name && item.old_name !== item.name

  return (
    <>
      <tr style={{ background: c.bgVar }}>
        <td style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '12px',
          fontWeight: 700,
          color: c.color,
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
          color: isLocked || kind === 'unchanged' ? 'var(--text-muted)' : 'var(--text-primary)',
          padding: '5px 10px 5px 0',
        }}>
          {nameChanged
            ? <>{item.old_name} <span style={{ color: 'var(--text-muted)' }}>→</span> {item.name}</>
            : item.name}
          {isLocked && (
            <span style={{ marginLeft: '6px', fontSize: '10px', color: 'var(--text-muted)' }}>
              (completed)
            </span>
          )}
        </td>
      </tr>
      {isChanged && (item.old_steps_spec || item.new_steps_spec) && (
        <tr style={{ background: c.bgVar }}>
          <td />
          <td />
          <td style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-muted)',
            padding: '0 10px 5px 0',
          }}>
            <span style={{ color: 'var(--color-error)', opacity: 0.7 }}>{item.old_steps_spec}</span>
            {' → '}
            <span style={{ color: 'var(--color-success)', opacity: 0.7 }}>{item.new_steps_spec}</span>
          </td>
        </tr>
      )}
    </>
  )
}

export function DiffTable({ diff }: DiffTableProps) {
  const totalAdded = diff.added.length
  const totalRemoved = diff.removed.length
  const totalChanged = diff.changed.length
  const totalUnchanged = (diff.unchanged ?? []).length
  const totalLocked = (diff.completed_locked ?? []).length
  const hasActionable = totalAdded + totalRemoved + totalChanged > 0

  if (!hasActionable) return null

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
        <div style={{ display: 'flex', gap: '8px', marginLeft: 'auto', flexWrap: 'wrap' }}>
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
          {totalUnchanged > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              ={totalUnchanged} unchanged
            </span>
          )}
          {totalLocked > 0 && (
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
              ⊘{totalLocked} locked
            </span>
          )}
        </div>
      </div>

      {/* Rows — actionable first, then informational */}
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
          {(diff.unchanged ?? []).map((item, i) => (
            <DiffRow key={`unchanged-${i}`} item={item} kind="unchanged" />
          ))}
          {(diff.completed_locked ?? []).map((item, i) => (
            <DiffRow key={`locked-${i}`} item={item} kind="completed_locked" />
          ))}
        </tbody>
      </table>
    </div>
  )
}

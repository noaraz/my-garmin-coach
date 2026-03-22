import type { ActivePlan } from '../../api/types'
import { useIsMobile } from '../../hooks/useIsMobile'

interface ActivePlanCardProps {
  plan: ActivePlan
  onUploadNew: () => void
  onDelete: () => void
}

export function ActivePlanCard({ plan, onUploadNew, onDelete }: ActivePlanCardProps) {
  const isMobile = useIsMobile()
  const startDate = new Date(plan.start_date + 'T00:00:00').toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  return (
    <div
      data-testid="active-plan-card"
      style={{
        border: '1px solid var(--border-strong)',
        borderLeft: '3px solid var(--accent)',
        borderRadius: '6px',
        padding: '16px 20px',
        background: 'var(--bg-surface)',
        marginBottom: '24px',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            marginBottom: '4px',
          }}>
            Current Plan
          </div>
          <div style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            wordBreak: 'break-word',
          }}>
            {plan.name}
          </div>
          <div style={{
            display: 'flex',
            gap: '14px',
            marginTop: '6px',
            flexWrap: 'wrap',
          }}>
            <span style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-secondary)',
            }}>
              Started {startDate}
            </span>
            {plan.workout_count != null && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '11px',
                color: 'var(--text-secondary)',
              }}>
                {plan.workout_count} workout{plan.workout_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: '8px', flexShrink: 0, alignItems: 'center', width: isMobile ? '100%' : undefined, marginTop: isMobile ? '12px' : undefined }}>
          <button
            onClick={onUploadNew}
            aria-label="Upload or update plan"
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '7px 14px',
              borderRadius: '4px',
              border: '1px solid var(--accent)',
              background: 'transparent',
              color: 'var(--accent)',
              cursor: 'pointer',
              width: isMobile ? '100%' : undefined,
            }}
          >
            Upload / Update Plan
          </button>
          <button
            onClick={onDelete}
            aria-label="Delete plan"
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '7px 14px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              width: isMobile ? '100%' : undefined,
            }}
          >
            Delete Plan
          </button>
        </div>
      </div>
    </div>
  )
}

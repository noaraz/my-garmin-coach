import type { ActivePlan } from '../../api/types'

interface DeletePlanModalProps {
  plan: ActivePlan
  onConfirm: () => void
  onCancel: () => void
  isDeleting: boolean
}

export function DeletePlanModal({ plan, onConfirm, onCancel, isDeleting }: DeletePlanModalProps) {
  const count = plan.workout_count ?? 0

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-plan-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel() }}
    >
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '28px 32px',
        maxWidth: '420px',
        width: '100%',
        boxShadow: '0 8px 32px var(--shadow-overlay)',
      }}>
        <h2
          id="delete-plan-title"
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '16px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '10px',
          }}
        >
          Delete plan?
        </h2>
        <p style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
          marginBottom: '6px',
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>{plan.name}</strong>
        </p>
        {count > 0 && (
          <p style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '13px',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
            marginBottom: '20px',
          }}>
            This will remove all {count} scheduled workout{count !== 1 ? 's' : ''} from your calendar.
            Workout templates will remain in your library. This cannot be undone.
          </p>
        )}
        {count === 0 && (
          <p style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '13px',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
            marginBottom: '20px',
          }}>
            This cannot be undone.
          </p>
        )}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            disabled={isDeleting}
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              opacity: isDeleting ? 0.5 : 1,
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            aria-label="Confirm delete plan"
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              background: 'var(--color-error)',
              color: 'var(--text-on-accent)',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              opacity: isDeleting ? 0.65 : 1,
            }}
          >
            {isDeleting ? 'Deleting…' : 'Delete Plan'}
          </button>
        </div>
      </div>
    </div>
  )
}

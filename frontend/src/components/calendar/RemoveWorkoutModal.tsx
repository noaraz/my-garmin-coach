interface RemoveWorkoutModalProps {
  workoutName: string
  workoutDate: string
  isSyncedToGarmin: boolean
  onConfirm: () => void
  onCancel: () => void
  isRemoving: boolean
}

function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function RemoveWorkoutModal({ workoutName, workoutDate, isSyncedToGarmin, onConfirm, onCancel, isRemoving }: RemoveWorkoutModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="remove-workout-title"
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
          id="remove-workout-title"
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '16px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '10px',
          }}
        >
          Remove workout?
        </h2>
        <p style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
          marginBottom: '6px',
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>{workoutName}</strong>
          {' — '}
          {formatDate(workoutDate)}
        </p>
        <p style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
          marginBottom: '20px',
        }}>
          {isSyncedToGarmin
            ? 'This workout will also be removed from Garmin Connect. This cannot be undone.'
            : 'This cannot be undone.'}
        </p>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            disabled={isRemoving}
            aria-label="Cancel"
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
              cursor: isRemoving ? 'not-allowed' : 'pointer',
              opacity: isRemoving ? 0.5 : 1,
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isRemoving}
            aria-label="Confirm remove workout"
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
              cursor: isRemoving ? 'not-allowed' : 'pointer',
              opacity: isRemoving ? 0.65 : 1,
            }}
          >
            {isRemoving ? 'Removing…' : 'Remove'}
          </button>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useState, useCallback, useRef } from 'react'
import type { ScheduledWorkoutWithActivity, GarminActivity, WorkoutTemplate, SyncStatus } from '../../api/types'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'
import { formatDateHeader, formatPace } from '../../utils/formatting'
import { computeCompliance, type ComplianceLevel } from '../../utils/compliance'
import { useIsMobile } from '../../hooks/useIsMobile'
import { refreshActivity } from '../../api/client'

// ---------------------------------------------------------------------------
// Step rendering helpers
// ---------------------------------------------------------------------------

interface ParsedStep {
  type?: 'repeat'
  duration_sec?: number
  duration_distance_m?: number
  zone?: number
  repeat_count?: number
  steps?: ParsedStep[]
}

function formatStep(step: ParsedStep): string {
  if (step.duration_sec != null) {
    const mins = step.duration_sec / 60
    const label = mins >= 1 ? `${mins % 1 === 0 ? mins : mins.toFixed(1)}m` : `${step.duration_sec}s`
    return `${label} @ Z${step.zone}`
  }
  if (step.duration_distance_m != null) {
    const m = step.duration_distance_m
    const label = m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${m}m`
    return `${label} @ Z${step.zone}`
  }
  return `Z${step.zone}`
}

function StepList({ steps, indent = 0 }: { steps: ParsedStep[]; indent?: number }) {
  return (
    <>
      {steps.map((step, i) => {
        if (step.type === 'repeat' && step.steps) {
          return (
            <div key={i} style={{ paddingLeft: indent * 12 }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                {step.repeat_count}×
              </div>
              <StepList steps={step.steps} indent={indent + 1} />
            </div>
          )
        }
        return (
          <div key={i} style={{ paddingLeft: indent * 12, fontSize: '12px', color: 'var(--text-primary)' }}>
            {formatStep(step)}
          </div>
        )
      })}
    </>
  )
}

function WorkoutSteps({ stepsJson }: { stepsJson: string | null | undefined }) {
  if (!stepsJson) return null
  let steps: ParsedStep[]
  try {
    steps = JSON.parse(stepsJson)
  } catch {
    return null
  }
  if (!steps.length) return null
  return (
    <div
      style={{
        background: 'var(--bg-surface-2)',
        padding: '12px',
        borderRadius: '4px',
        marginBottom: '16px',
      }}
    >
      <div
        style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '10px',
          fontWeight: 600,
          letterSpacing: '0.05em',
          color: 'var(--text-muted)',
          marginBottom: '8px',
          textTransform: 'uppercase',
        }}
      >
        Workout Steps
      </div>
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.8, display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <StepList steps={steps} />
      </div>
    </div>
  )
}

interface WorkoutDetailPanelProps {
  workout?: ScheduledWorkoutWithActivity | null
  activity?: GarminActivity | null
  template?: WorkoutTemplate
  onClose: () => void
  onReschedule: (id: number, newDate: string) => void
  onRemove: (id: number) => void
  onUnpair: (scheduledId: number) => void
  onUpdateNotes: (id: number, notes: string) => void
  onNavigateToBuilder: (templateId: number) => void
  onSync?: (id: number) => Promise<void>
  onRefreshActivity?: (updated: GarminActivity) => void
}

function syncStatusLabel(status: SyncStatus): string {
  const labels: Record<SyncStatus, string> = {
    synced: '✓',
    pending: '○',
    modified: '~',
    failed: '✗',
  }
  return labels[status]
}

function syncStatusText(status: SyncStatus): string {
  const texts: Record<SyncStatus, string> = {
    synced: 'Synced to Garmin',
    pending: 'Pending sync',
    modified: 'Modified',
    failed: 'Sync failed',
  }
  return texts[status]
}

function zoneStripeColor(sportType: string | undefined): string {
  if (sportType === 'running') return 'var(--color-zone-1)'
  if (sportType === 'cycling') return 'var(--color-zone-2)'
  return 'var(--zone-default)'
}

function WorkoutDetailPlanned({
  workout,
  template,
  onReschedule,
  onRemove,
  onUpdateNotes,
  onNavigateToBuilder,
  onSync,
}: {
  workout: ScheduledWorkoutWithActivity
  template?: WorkoutTemplate
  onClose: () => void
  onReschedule: (id: number, newDate: string) => void
  onRemove: (id: number) => void
  onUpdateNotes: (id: number, notes: string) => void
  onNavigateToBuilder: (templateId: number) => void
  onSync?: (id: number) => Promise<void>
}) {
  const [localNotes, setLocalNotes] = useState(workout.notes ?? '')
  const [saved, setSaved] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const durationSec = template?.estimated_duration_sec ?? computeDurationFromSteps(template?.steps)
  const distanceM = template?.estimated_distance_m ?? computeDistanceFromSteps(template?.steps)
  const stripeColor = zoneStripeColor(template?.sport_type)

  // Clean up debounce timer on unmount
  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current) }, [])

  const flushNotes = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = null
    if (localNotes !== (workout.notes ?? '')) {
      onUpdateNotes(workout.id, localNotes)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    }
  }, [localNotes, workout.notes, workout.id, onUpdateNotes])

  const handleNotesChange = (value: string) => {
    setLocalNotes(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      onUpdateNotes(workout.id, value)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    }, 500)
  }

  const handleRemove = () => {
    onRemove(workout.id)
  }

  const handleSync = async () => {
    if (!onSync) return
    setIsSyncing(true)
    try {
      await onSync(workout.id)
    } catch {
      // Error is handled by the caller (status indicator retains value; button re-enables)
    } finally {
      setIsSyncing(false)
    }
  }

  const handleEdit = () => {
    if (template?.id) {
      onNavigateToBuilder(template.id)
    }
  }

  return (
    <div data-testid="workout-detail-planned">
      {/* Header stripe */}
      <div style={{ height: '6px', background: stripeColor }} />

      {/* Content */}
      <div style={{ padding: '20px' }}>
        {/* Workout name */}
        <div
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '4px',
          }}
        >
          {template?.name ?? 'Workout'}
        </div>

        {/* Date */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '16px',
          }}
        >
          {formatDateHeader(workout.date)}
        </div>

        {/* Metrics */}
        {(durationSec != null || distanceM != null) && (
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'baseline' }}>
            {durationSec != null && durationSec > 0 && (
              <span
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '20px',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                }}
              >
                {formatClock(durationSec)}
              </span>
            )}
            {distanceM != null && distanceM > 0 && (
              <span
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '20px',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                }}
              >
                {formatKm(distanceM)}
              </span>
            )}
          </div>
        )}

        {/* Workout Steps (parsed zones) */}
        <WorkoutSteps stepsJson={template?.steps} />

        {/* Sync status + button */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '20px',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{syncStatusLabel(workout.sync_status)}</span>
          <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif" }}>
            {syncStatusText(workout.sync_status)}
          </span>
          {onSync && (
            <button
              onClick={handleSync}
              disabled={isSyncing}
              style={{
                marginLeft: 'auto',
                padding: '4px 10px',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontSize: '12px',
                fontWeight: 600,
                cursor: isSyncing ? 'default' : 'pointer',
                opacity: isSyncing ? 0.6 : 1,
              }}
            >
              {isSyncing ? 'Syncing…' : 'Sync to Garmin'}
            </button>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label
              style={{
                fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                fontSize: '12px',
                color: 'var(--text-secondary)',
                minWidth: '80px',
              }}
            >
              Reschedule
            </label>
            <input
              type="date"
              value={workout.date}
              onChange={(e) => onReschedule(workout.id, e.target.value)}
              style={{
                flex: 1,
                padding: '6px 8px',
                borderRadius: '4px',
                border: '1px solid var(--border)',
                background: 'var(--input-bg)',
                color: 'var(--text-primary)',
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '12px',
              }}
            />
          </div>

          <button
            onClick={handleEdit}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Edit in Builder
          </button>

          <button
            onClick={handleRemove}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: '1px solid var(--color-error-border-weak)',
              background: 'var(--bg-surface)',
              color: 'var(--color-error)',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Remove
          </button>
        </div>

        {/* Notes */}
        <div>
          <div
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            Notes
            {saved && (
              <span
                style={{
                  color: 'var(--color-success)',
                  fontSize: '10px',
                  fontWeight: 500,
                }}
              >
                Saved
              </span>
            )}
          </div>
        {template?.description && (
            <div
              style={{
                fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                fontSize: '12px',
                color: 'var(--text-secondary)',
                marginBottom: '6px',
                fontStyle: 'italic',
              }}
            >
              {template.description}
            </div>
          )}
          <textarea
            value={localNotes}
            onChange={(e) => handleNotesChange(e.target.value)}
            onBlur={flushNotes}
            placeholder="Add notes..."
            rows={4}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'var(--input-bg)',
              color: 'var(--text-primary)',
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '12px',
              resize: 'vertical',
            }}
          />
        </div>
      </div>
    </div>
  )
}

function complianceBadgeLabel(level: ComplianceLevel): string {
  const labels: Record<ComplianceLevel, string> = {
    on_target: 'ON TARGET',
    close: 'CLOSE',
    off_target: 'OFF TARGET',
    completed_no_plan: 'COMPLETED',
    unplanned: 'UNPLANNED',
    missed: 'MISSED',
  }
  return labels[level]
}

function WorkoutDetailCompleted({
  workout,
  template,
  onUnpair,
  onUpdateNotes,
}: {
  workout: ScheduledWorkoutWithActivity
  template?: WorkoutTemplate
  onClose: () => void
  onUnpair: (scheduledId: number) => void
  onUpdateNotes: (id: number, notes: string) => void
}) {
  const [localNotes, setLocalNotes] = useState(workout.notes ?? '')
  const [saved, setSaved] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const durationSec = template?.estimated_duration_sec ?? computeDurationFromSteps(template?.steps)
  const distanceM = template?.estimated_distance_m ?? computeDistanceFromSteps(template?.steps)

  const planned = { duration_sec: durationSec, distance_m: distanceM }
  const actual = workout.activity
    ? { duration_sec: workout.activity.duration_sec, distance_m: workout.activity.distance_m }
    : null
  const compliance = computeCompliance(planned, actual)

  // Clean up debounce timer on unmount
  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current) }, [])

  const flushNotes = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = null
    if (localNotes !== (workout.notes ?? '')) {
      onUpdateNotes(workout.id, localNotes)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    }
  }, [localNotes, workout.notes, workout.id, onUpdateNotes])

  const handleNotesChange = (value: string) => {
    setLocalNotes(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      onUpdateNotes(workout.id, value)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    }, 500)
  }

  const handleUnpair = () => {
    onUnpair(workout.id)
  }

  return (
    <div data-testid="workout-detail-completed">
      {/* Header stripe */}
      <div style={{ height: '6px', background: compliance.color }} />

      {/* Content */}
      <div style={{ padding: '20px' }}>
        {/* Workout name */}
        <div
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '4px',
          }}
        >
          {template?.name ?? 'Workout'}
        </div>

        {/* Date */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '12px',
          }}
        >
          {formatDateHeader(workout.date)}
        </div>

        {/* Compliance badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            borderRadius: '4px',
            background: compliance.color,
            marginBottom: '16px',
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--text-on-accent)',
              letterSpacing: '0.05em',
            }}
          >
            {complianceBadgeLabel(compliance.level)}
          </span>
        </div>

        {/* Deviation percentage */}
        {compliance.percentage != null && compliance.metric != null && (
          <div
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-muted)',
              marginBottom: '16px',
            }}
          >
            {compliance.metric === 'duration' ? 'Duration' : 'Distance'}{' '}
            {compliance.direction === 'over' ? '+' : compliance.direction === 'under' ? '-' : ''}
            {Math.abs(compliance.percentage - 100)}%
          </div>
        )}

        {/* Planned vs Actual */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            marginBottom: '20px',
          }}
        >
          {/* Planned */}
          <div
            style={{
              background: 'var(--bg-surface-2)',
              padding: '12px',
              borderRadius: '4px',
            }}
          >
            <div
              style={{
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.05em',
                color: 'var(--text-muted)',
                marginBottom: '8px',
                textTransform: 'uppercase',
              }}
            >
              Planned
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {durationSec != null && durationSec > 0 && (
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '16px',
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                  }}
                >
                  {formatClock(durationSec)}
                </div>
              )}
              {distanceM != null && distanceM > 0 && (
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {formatKm(distanceM)}
                </div>
              )}
            </div>
          </div>

          {/* Actual */}
          {workout.activity && (
            <div
              style={{
                background: 'var(--bg-surface-2)',
                padding: '12px',
                borderRadius: '4px',
              }}
            >
              <div
                style={{
                  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                  textTransform: 'uppercase',
                }}
              >
                Actual
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '16px',
                    fontWeight: 700,
                    color: compliance.color,
                  }}
                >
                  {formatClock(workout.activity.duration_sec)}
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {formatKm(workout.activity.distance_m)}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Activity details */}
        {workout.activity && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              marginBottom: '20px',
            }}
          >
            {workout.activity.avg_pace_sec_per_km != null && (
              <div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginBottom: '4px',
                  }}
                >
                  Avg Pace
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {formatPace(workout.activity.avg_pace_sec_per_km)}
                </div>
              </div>
            )}

            {workout.activity.avg_hr != null && (
              <div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginBottom: '4px',
                  }}
                >
                  Avg HR
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {Math.round(workout.activity.avg_hr)} bpm
                </div>
              </div>
            )}

            {workout.activity.max_hr != null && (
              <div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginBottom: '4px',
                  }}
                >
                  Max HR
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {Math.round(workout.activity.max_hr)} bpm
                </div>
              </div>
            )}

            {workout.activity.calories != null && (
              <div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginBottom: '4px',
                  }}
                >
                  Calories
                </div>
                <div
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  {workout.activity.calories}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Unpair button */}
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={handleUnpair}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Unpair Activity
          </button>
        </div>

        {/* Notes */}
        <div>
          <div
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
              marginBottom: '6px',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            Notes
            {saved && (
              <span
                style={{
                  color: 'var(--color-success)',
                  fontSize: '10px',
                  fontWeight: 500,
                }}
              >
                Saved
              </span>
            )}
          </div>
          <textarea
            value={localNotes}
            onChange={(e) => handleNotesChange(e.target.value)}
            onBlur={flushNotes}
            placeholder="Add notes..."
            rows={4}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              background: 'var(--input-bg)',
              color: 'var(--text-primary)',
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '12px',
              resize: 'vertical',
            }}
          />
        </div>
      </div>
    </div>
  )
}

function WorkoutDetailUnplanned({
  activity,
  onRefreshActivity,
}: {
  activity: GarminActivity
  onClose: () => void
  onRefreshActivity?: (updated: GarminActivity) => void
}) {
  const [refreshing, setRefreshing] = useState(false)
  const greyColor = 'var(--color-compliance-grey)'

  return (
    <div data-testid="workout-detail-unplanned">
      {/* Header stripe */}
      <div style={{ height: '6px', background: greyColor }} />

      {/* Content */}
      <div style={{ padding: '20px' }}>
        {/* Activity name */}
        <div
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '4px',
          }}
        >
          {activity.name}
        </div>

        {/* Date */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '12px',
          }}
        >
          {formatDateHeader(activity.date)}
        </div>

        {/* Unplanned badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            borderRadius: '4px',
            background: greyColor,
            marginBottom: '16px',
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--text-on-accent)',
              letterSpacing: '0.05em',
            }}
          >
            UNPLANNED
          </span>
        </div>

        {/* Metrics */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', alignItems: 'baseline' }}>
          <span
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '20px',
              fontWeight: 700,
              color: 'var(--text-primary)',
            }}
          >
            {formatClock(activity.duration_sec)}
          </span>
          <span
            style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '20px',
              fontWeight: 700,
              color: 'var(--text-primary)',
            }}
          >
            {formatKm(activity.distance_m)}
          </span>
        </div>

        {/* Activity details grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
          }}
        >
          {activity.avg_pace_sec_per_km != null && (
            <div>
              <div
                style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginBottom: '4px',
                }}
              >
                Avg Pace
              </div>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {formatPace(activity.avg_pace_sec_per_km)}
              </div>
            </div>
          )}

          {activity.avg_hr != null && (
            <div>
              <div
                style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginBottom: '4px',
                }}
              >
                Avg HR
              </div>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {Math.round(activity.avg_hr)} bpm
              </div>
            </div>
          )}

          {activity.max_hr != null && (
            <div>
              <div
                style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginBottom: '4px',
                }}
              >
                Max HR
              </div>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {Math.round(activity.max_hr)} bpm
              </div>
            </div>
          )}

          {activity.calories != null && (
            <div>
              <div
                style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginBottom: '4px',
                }}
              >
                Calories
              </div>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {activity.calories}
              </div>
            </div>
          )}
        </div>

        {/* Refresh button */}
        {onRefreshActivity && (
          <button
            onClick={async () => {
              setRefreshing(true)
              try {
                const updated = await refreshActivity(activity.id)
                onRefreshActivity(updated)
              } catch {
                // swallow — button re-enables in finally
              } finally {
                setRefreshing(false)
              }
            }}
            disabled={refreshing}
            aria-label={refreshing ? 'Refreshing activity data from Garmin' : 'Refresh from Garmin'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--bg-surface-2)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '8px 14px',
              color: 'var(--text-primary)',
              cursor: refreshing ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              opacity: refreshing ? 0.6 : 1,
              marginTop: '16px',
            }}
          >
            {refreshing ? 'Refreshing\u2026' : 'Refresh from Garmin'}
          </button>
        )}
      </div>
    </div>
  )
}

export function WorkoutDetailPanel({
  workout,
  activity,
  template,
  onClose,
  onReschedule,
  onRemove,
  onUnpair,
  onUpdateNotes,
  onNavigateToBuilder,
  onSync,
  onRefreshActivity,
}: WorkoutDetailPanelProps) {
  const isMobile = useIsMobile()

  // Escape key listener
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  // State routing
  const isPlanned = workout != null && workout.activity == null
  const isCompleted = workout != null && workout.activity != null
  const isUnplannedOnly = workout == null && activity != null

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="panel-backdrop"
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.3)',
          zIndex: 20,
        }}
      />

      {/* Panel */}
      <div
        data-testid="workout-detail-panel"
        className={isMobile ? 'workout-detail-panel-mobile' : undefined}
        style={isMobile ? undefined : {
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '380px',
          background: 'var(--bg-surface)',
          zIndex: 21,
          overflowY: 'auto',
          boxShadow: '-2px 0 8px rgba(0,0,0,0.15)',
          animation: 'slideInRight 0.2s ease-out',
        }}
      >
        {/* Close button - always visible */}
        <button
          onClick={onClose}
          aria-label="Close panel"
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: '20px',
            lineHeight: 1,
            padding: '4px',
            zIndex: 10,
          }}
        >
          ✕
        </button>

        {/* Content routing */}
        {isPlanned && workout && (
          <WorkoutDetailPlanned
            workout={workout}
            template={template}
            onClose={onClose}
            onReschedule={onReschedule}
            onRemove={onRemove}
            onUpdateNotes={onUpdateNotes}
            onNavigateToBuilder={onNavigateToBuilder}
            onSync={onSync}
          />
        )}

        {isCompleted && workout && (
          <WorkoutDetailCompleted
            workout={workout}
            template={template}
            onClose={onClose}
            onUnpair={onUnpair}
            onUpdateNotes={onUpdateNotes}
          />
        )}

        {isUnplannedOnly && activity && (
          <WorkoutDetailUnplanned activity={activity} onClose={onClose} onRefreshActivity={onRefreshActivity} />
        )}
      </div>
    </>
  )
}

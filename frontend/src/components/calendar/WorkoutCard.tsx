import { useState } from 'react'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate, SyncStatus, GarminActivity } from '../../api/types'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'
import { computeCompliance } from '../../utils/compliance'

interface WorkoutCardProps {
  workout: ScheduledWorkoutWithActivity
  template: WorkoutTemplate | undefined
  onRemove: (id: number) => void
  onCardClick?: (workout: ScheduledWorkoutWithActivity) => void
  displayName?: string
  compact?: boolean
  planName?: string
}

function syncStatusClass(status: SyncStatus): string {
  const classes: Record<SyncStatus, string> = {
    synced: 'text-green-500',
    pending: 'text-gray-400',
    modified: 'text-yellow-500',
    failed: 'text-red-500',
  }
  return classes[status]
}

function syncStatusLabel(status: SyncStatus): string {
  const labels: Record<SyncStatus, string> = {
    synced: '\u2713',
    pending: '\u25CB',
    modified: '~',
    failed: '\u2717',
  }
  return labels[status]
}

function zoneStripeColor(sportType: string | undefined): string {
  if (sportType === 'running') return 'var(--color-zone-1)'
  if (sportType === 'cycling') return 'var(--color-zone-2)'
  return 'var(--zone-default)'
}

function getComplianceStripeColor(
  template: WorkoutTemplate | undefined,
  activity: GarminActivity | null | undefined,
  durationSec: number | null,
  distanceM: number | null,
): string | null {
  if (!activity) return null
  const planned = template ? { duration_sec: durationSec, distance_m: distanceM } : null
  const actual = { duration_sec: activity.duration_sec, distance_m: activity.distance_m }
  const result = computeCompliance(planned, actual)
  return result.color
}


export function WorkoutCard({ workout, template, onRemove, onCardClick, displayName, compact, planName }: WorkoutCardProps) {
  const [removeHover, setRemoveHover] = useState(false)

  const durationSec = template?.estimated_duration_sec ?? computeDurationFromSteps(template?.steps)
  const distanceM = template?.estimated_distance_m ?? computeDistanceFromSteps(template?.steps)
  const hasDuration = durationSec != null && durationSec > 0
  const hasDistance = distanceM != null && distanceM > 0

  const complianceColor = getComplianceStripeColor(template, workout.activity, durationSec, distanceM)
  const stripeColor = complianceColor ?? zoneStripeColor(template?.sport_type)

  const handleCardClick = () => {
    if (onCardClick) {
      onCardClick(workout)
    }
  }

  return (
    <div
      onClick={handleCardClick}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'stretch',
        background: 'var(--card-bg)',
        borderRadius: compact ? '3px' : '5px',
        border: '1px solid var(--border)',
        userSelect: 'none',
        boxShadow: compact ? 'none' : '0 1px 3px rgba(0,0,0,0.12)',
        overflow: 'hidden',
        cursor: onCardClick ? 'pointer' : 'default',
      }}
      data-testid="workout-card"
    >
      {/* Left compliance/zone stripe */}
      <div style={{ width: compact ? '3px' : '4px', background: stripeColor, flexShrink: 0 }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, padding: compact ? '3px 4px' : '8px 0 8px 8px' }}>

        {/* Workout name */}
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: compact ? '10px' : '14px',
          fontWeight: 600,
          letterSpacing: '0.02em',
          color: 'var(--text-primary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: 1.2,
        }}>
          {displayName ?? template?.name ?? 'Workout'}
        </div>

        {/* Plan badge */}
        {planName && workout.training_plan_id != null && !compact && (
          <div style={{
            display: 'inline-block',
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '9px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--accent)',
            background: 'var(--accent-subtle)',
            borderRadius: '3px',
            padding: '1px 5px',
            marginTop: '3px',
          }}>
            {planName}
          </div>
        )}

        {/* Summary: duration + distance — prominent, like TrainingPeaks */}
        {(hasDuration || hasDistance) && (
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: compact ? '4px' : '8px',
            marginTop: compact ? '1px' : '4px',
            flexWrap: 'wrap',
          }}>
            {hasDuration && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: compact ? '9px' : '13px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1,
              }}>
                {formatClock(durationSec!)}
              </span>
            )}
            {hasDistance && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: compact ? '9px' : '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                lineHeight: 1,
              }}>
                {formatKm(distanceM!)}
              </span>
            )}
          </div>
        )}

        {/* Actual activity data when matched */}
        {workout.activity && !compact && (
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '6px',
            marginTop: '3px',
          }}>
            <span style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '10px',
              fontWeight: 600,
              color: complianceColor ?? 'var(--text-muted)',
              lineHeight: 1,
            }}>
              {formatClock(workout.activity.duration_sec)}
            </span>
            <span style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '10px',
              color: 'var(--text-muted)',
              lineHeight: 1,
            }}>
              {formatKm(workout.activity.distance_m)}
            </span>
            {workout.activity.avg_hr != null && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '10px',
                color: 'var(--text-muted)',
                lineHeight: 1,
              }}>
                {Math.round(workout.activity.avg_hr)} bpm
              </span>
            )}
          </div>
        )}

        {/* Description — one row per comma-segment (shown in all views) */}
        {template?.description && (
          <div style={{ marginTop: compact ? '2px' : '5px', display: 'flex', flexDirection: 'column', gap: '1px' }}>
            {template.description.split(',').map((seg, i) => (
              <span key={i} style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: compact ? '9px' : '10px',
                color: 'var(--text-secondary)',
                lineHeight: 1.4,
              }}>
                {seg.trim()}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Right column: sync icon + remove (hidden in compact/month view) */}
      <div style={{ display: compact ? 'none' : 'flex', flexDirection: 'column', alignItems: 'center', padding: '6px 6px 6px 2px', gap: '4px', flexShrink: 0 }}>
        <span
          data-sync={workout.sync_status}
          className={`text-xs font-mono ${syncStatusClass(workout.sync_status)}`}
          aria-label={`sync status: ${workout.sync_status}`}
          style={{ fontSize: '11px', lineHeight: 1 }}
        >
          {syncStatusLabel(workout.sync_status)}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(workout.id) }}
          aria-label="Remove workout"
          title="Remove workout"
          onMouseEnter={() => setRemoveHover(true)}
          onMouseLeave={() => setRemoveHover(false)}
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: removeHover ? 'var(--color-zone-5)' : 'var(--text-secondary)',
            fontSize: '12px', padding: '0 2px', lineHeight: 1,
          }}
        >&#x2715;</button>
      </div>
    </div>
  )
}

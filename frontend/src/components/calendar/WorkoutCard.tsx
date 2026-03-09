import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ScheduledWorkout, WorkoutTemplate, SyncStatus } from '../../api/types'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'

interface WorkoutCardProps {
  workout: ScheduledWorkout
  template: WorkoutTemplate | undefined
  onRemove: (id: number) => void
  displayName?: string
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
    synced: '✓',
    pending: '○',
    modified: '~',
    failed: '✗',
  }
  return labels[status]
}

function zoneStripeColor(sportType: string | undefined): string {
  if (sportType === 'running') return 'var(--color-zone-1)'
  if (sportType === 'cycling') return 'var(--color-zone-2)'
  return 'var(--zone-default)'
}


export function WorkoutCard({ workout, template, onRemove, displayName }: WorkoutCardProps) {
  const [removeHover, setRemoveHover] = useState(false)
  const navigate = useNavigate()
  const stripeColor = zoneStripeColor(template?.sport_type)

  const handleCardClick = () => {
    if (workout.workout_template_id != null) {
      navigate(`/builder?id=${workout.workout_template_id}`)
    }
  }

  const durationSec = template?.estimated_duration_sec ?? computeDurationFromSteps(template?.steps)
  const distanceM = template?.estimated_distance_m ?? computeDistanceFromSteps(template?.steps)
  const hasDuration = durationSec != null && durationSec > 0
  const hasDistance = distanceM != null && distanceM > 0

  return (
    <div
      onClick={handleCardClick}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'stretch',
        background: 'var(--card-bg)',
        borderRadius: '5px',
        border: '1px solid var(--border)',
        userSelect: 'none',
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        overflow: 'hidden',
        cursor: workout.workout_template_id != null ? 'pointer' : 'default',
      }}
      data-testid="workout-card"
    >
      {/* Left zone stripe */}
      <div style={{ width: '4px', background: stripeColor, flexShrink: 0 }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, padding: '8px 0 8px 8px' }}>

        {/* Workout name */}
        <div style={{
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '14px',
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

        {/* Summary: duration + distance — prominent, like TrainingPeaks */}
        {(hasDuration || hasDistance) && (
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px',
            marginTop: '4px',
            flexWrap: 'wrap',
          }}>
            {hasDuration && (
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1,
              }}>
                {formatClock(durationSec!)}
              </span>
            )}
            {hasDistance && (
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                lineHeight: 1,
              }}>
                {formatKm(distanceM!)}
              </span>
            )}
          </div>
        )}

        {/* Description — one row per comma-segment */}
        {template?.description && (
          <div style={{ marginTop: '5px', display: 'flex', flexDirection: 'column', gap: '1px' }}>
            {template.description.split(',').map((seg, i) => (
              <span key={i} style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color: 'var(--text-secondary)',
                lineHeight: 1.4,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {seg.trim()}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Right column: sync icon + remove */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '6px 6px 6px 2px', gap: '4px', flexShrink: 0 }}>
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
        >✕</button>
      </div>
    </div>
  )
}

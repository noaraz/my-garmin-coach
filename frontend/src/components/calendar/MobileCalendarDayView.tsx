import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../../api/types'
import { addDays } from 'date-fns'
import { toDateString, formatPace } from '../../utils/formatting'
import { formatClock, computeDurationFromSteps, formatKm, computeDistanceFromSteps } from '../../utils/workoutStats'

interface MobileCalendarDayViewProps {
  weekStart: Date
  selectedDay: string
  onSelectDay: (date: string) => void
  workouts: ScheduledWorkoutWithActivity[]
  templates: WorkoutTemplate[]
  unplannedActivities: GarminActivity[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
}

function parseDateParts(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  const dayAbbr = d.toLocaleDateString('en-GB', { weekday: 'short' }).toUpperCase()
  const dayNum = d.getDate()
  const isToday = new Date().toISOString().slice(0, 10) === dateStr
  return { dayAbbr, dayNum, isToday }
}

export function MobileCalendarDayView({
  weekStart,
  selectedDay,
  onSelectDay,
  workouts,
  templates,
  unplannedActivities,
  onAddWorkout,
  onRemove,
  onWorkoutClick,
  onActivityClick,
}: MobileCalendarDayViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => toDateString(addDays(weekStart, i)))

  const dayWorkouts = workouts.filter(w => w.date === selectedDay)
  const dayActivities = unplannedActivities.filter(a => a.date === selectedDay)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* 7-day strip */}
      <div
        data-testid="mobile-day-strip"
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-surface)',
          flexShrink: 0,
        }}
      >
        {days.map(date => {
          const { dayAbbr, dayNum, isToday } = parseDateParts(date)
          const isSelected = date === selectedDay
          const hasWorkout = workouts.some(w => w.date === date) || unplannedActivities.some(a => a.date === date)

          return (
            <button
              key={date}
              aria-label={`Select ${date}`}
              aria-pressed={isSelected}
              onClick={() => onSelectDay(date)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '8px 2px 6px',
                border: 'none',
                background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                cursor: 'pointer',
                borderBottom: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              <span style={{
                fontFamily: 'var(--font-family-display)',
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: isSelected ? 'var(--accent)' : 'var(--text-muted)',
                marginBottom: 2,
              }}>{dayAbbr}</span>
              <span style={{
                fontFamily: 'var(--font-family-display)',
                fontSize: 18,
                fontWeight: 700,
                color: isToday ? 'var(--accent)' : isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                lineHeight: 1,
              }}>{dayNum}</span>
              {/* dot indicator for days with workouts */}
              <div style={{
                width: 4,
                height: 4,
                borderRadius: '50%',
                marginTop: 3,
                background: hasWorkout
                  ? (isSelected ? 'var(--accent)' : 'var(--text-muted)')
                  : 'transparent',
              }} />
            </button>
          )
        })}
      </div>

      {/* Day content */}
      <div
        data-testid="mobile-day-list"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 16px',
          paddingBottom: 'calc(var(--bottom-tab-height) + 16px)',
        }}
      >
        {dayWorkouts.length === 0 && dayActivities.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '48px 0',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-family-body)',
            fontSize: 14,
          }}>
            Rest day
          </div>
        )}

        {dayWorkouts.map(workout => {
          const template = templates.find(t => t.id === workout.workout_template_id)
          const name = template?.name ?? 'Workout'
          const durationSec = template?.estimated_duration_sec ?? computeDurationFromSteps(template?.steps)
          const distanceM = template?.estimated_distance_m ?? computeDistanceFromSteps(template?.steps)
          const hasDuration = durationSec != null && durationSec > 0
          const hasDistance = distanceM != null && distanceM > 0
          const isCompleted = workout.completed
          const isSynced = workout.sync_status === 'synced'

          // If matched activity, show its actual stats
          const act = workout.activity
          const actDuration = act?.duration_sec
          const actDistance = act?.distance_m
          const actPace = act?.avg_pace_sec_per_km

          return (
            <div
              key={workout.id}
              data-testid={`mobile-workout-card-${workout.id}`}
              onClick={() => onWorkoutClick?.(workout)}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '14px 14px 14px 16px',
                marginBottom: 10,
                cursor: onWorkoutClick ? 'pointer' : undefined,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0, marginRight: 8 }}>
                  <div style={{
                    fontFamily: 'var(--font-family-display)',
                    fontWeight: 700,
                    fontSize: 16,
                    color: 'var(--text-primary)',
                    marginBottom: 4,
                    lineHeight: 1.2,
                  }}>{name}</div>

                  {/* Planned stats */}
                  {(hasDuration || hasDistance) && (
                    <div style={{
                      fontFamily: 'var(--font-family-mono)',
                      fontSize: 13,
                      color: 'var(--text-secondary)',
                      marginBottom: 4,
                    }}>
                      {hasDuration && formatClock(durationSec!)}
                      {hasDuration && hasDistance && ' · '}
                      {hasDistance && formatKm(distanceM!)}
                    </div>
                  )}

                  {/* Actual activity stats */}
                  {act && (
                    <div style={{
                      fontFamily: 'var(--font-family-mono)',
                      fontSize: 12,
                      color: 'var(--text-muted)',
                      marginBottom: 6,
                    }}>
                      {actDuration != null && formatClock(actDuration)}
                      {actDuration != null && actDistance != null && ' · '}
                      {actDistance != null && formatKm(actDistance)}
                      {actPace != null && ` · ${formatPace(actPace)}`}
                    </div>
                  )}

                  {/* Description — NOTE: WorkoutCard has equivalent rendering; keep in sync */}
                  {template?.description && (
                    <div style={{ marginBottom: 6, display: 'flex', flexDirection: 'column', gap: '1px' }}>
                      {template.description.split(',').map((seg, i) => (
                        <span key={i} style={{
                          fontFamily: 'var(--font-family-mono)',
                          fontSize: 11,
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

                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {isCompleted && (
                      <span style={{
                        fontSize: 10,
                        fontWeight: 700,
                        fontFamily: 'var(--font-family-display)',
                        letterSpacing: '0.08em',
                        padding: '2px 7px',
                        borderRadius: 3,
                        background: 'var(--color-success-bg)',
                        color: '#22c55e',
                        textTransform: 'uppercase',
                      }}>Done</span>
                    )}
                    {isSynced && !isCompleted && (
                      <span style={{
                        fontSize: 10,
                        fontWeight: 700,
                        fontFamily: 'var(--font-family-display)',
                        letterSpacing: '0.08em',
                        padding: '2px 7px',
                        borderRadius: 3,
                        background: 'var(--bg-surface-2)',
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                      }}>Synced</span>
                    )}
                  </div>
                </div>

                <button
                  aria-label={`Remove ${name}`}
                  onClick={e => { e.stopPropagation(); onRemove(workout.id) }}
                  style={{
                    width: 28,
                    height: 28,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    borderRadius: 4,
                    flexShrink: 0,
                    fontSize: 14,
                  }}
                >✕</button>
              </div>
            </div>
          )
        })}

        {dayActivities.map(activity => (
          <div
            key={activity.id}
            data-testid={`mobile-activity-card-${activity.id}`}
            onClick={() => onActivityClick?.(activity)}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderLeft: '3px solid var(--accent)',
              borderRadius: 10,
              padding: '14px 16px',
              marginBottom: 10,
              cursor: onActivityClick ? 'pointer' : undefined,
            }}
          >
            <div style={{
              fontFamily: 'var(--font-family-display)',
              fontWeight: 700,
              fontSize: 16,
              color: 'var(--text-primary)',
              marginBottom: 4,
            }}>{activity.name}</div>
            <div style={{
              fontFamily: 'var(--font-family-mono)',
              fontSize: 13,
              color: 'var(--text-secondary)',
            }}>
              {formatClock(activity.duration_sec)}
              {activity.distance_m > 0 && ` · ${formatKm(activity.distance_m)}`}
              {activity.avg_pace_sec_per_km != null && ` · ${formatPace(activity.avg_pace_sec_per_km)}`}
            </div>
          </div>
        ))}

        {/* Add workout button */}
        <button
          aria-label={`Add workout on ${selectedDay}`}
          onClick={() => onAddWorkout(selectedDay)}
          style={{
            width: '100%',
            padding: '14px',
            border: '1px dashed var(--border-strong)',
            borderRadius: 10,
            background: 'transparent',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-family-display)',
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          + Add Workout
        </button>
      </div>
    </div>
  )
}

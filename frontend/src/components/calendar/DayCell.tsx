import { useState } from 'react'
import type { ScheduledWorkout, WorkoutTemplate } from '../../api/types'
import { WorkoutCard } from './WorkoutCard'

interface DayCellProps {
  date: string
  workouts: ScheduledWorkout[]
  templates: WorkoutTemplate[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
  getDisplayName?: (workout: ScheduledWorkout) => string | undefined
}

function parseDateParts(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  const dayName = d.toLocaleDateString('en-GB', { weekday: 'short' }).toUpperCase()
  const dayNum = d.getDate()
  const isToday = new Date().toISOString().slice(0, 10) === dateStr
  return { dayName, dayNum, isToday }
}

export function DayCell({ date, workouts, templates, onAddWorkout, onRemove, getDisplayName }: DayCellProps) {
  const [hovering, setHovering] = useState(false)
  const { dayName, dayNum, isToday } = parseDateParts(date)

  const getTemplate = (workout: ScheduledWorkout) =>
    templates.find(t => t.id === workout.workout_template_id)

  return (
    <div
      data-testid="day-column"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
        borderRight: '1px solid var(--border)',
        background: 'var(--bg-surface)',
      }}
    >
      {/* Column header */}
      <div
        data-testid="day-header"
        style={{
          padding: '8px 8px 6px',
          borderBottom: '1px solid var(--border)',
          background: isToday ? 'var(--today-bg)' : 'var(--bg-surface-2)',
          textAlign: 'center',
          flexShrink: 0,
        }}
      >
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.12em',
          color: isToday ? 'var(--accent)' : 'var(--text-secondary)',
          textTransform: 'uppercase',
          lineHeight: 1,
          marginBottom: '4px',
        }}>
          {dayName}
        </div>
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '22px',
          fontWeight: 700,
          color: isToday ? 'var(--accent)' : 'var(--text-primary)',
          lineHeight: 1,
        }}>
          {dayNum}
        </div>
      </div>

      {/* Workout cards — clicking empty area opens picker */}
      <div
        style={{
          flex: 1,
          padding: '6px 6px',
          display: 'flex',
          flexDirection: 'column',
          gap: '5px',
          overflowY: 'auto',
          cursor: 'pointer',
        }}
        onClick={() => onAddWorkout(date)}
      >
        {workouts.map(workout => (
          <div key={workout.id} onClick={e => e.stopPropagation()}>
            <WorkoutCard
              workout={workout}
              template={getTemplate(workout)}
              onRemove={onRemove}
              displayName={getDisplayName ? getDisplayName(workout) : undefined}
            />
          </div>
        ))}
      </div>

      {/* Add workout — subtle dashed button */}
      <button
        onClick={() => onAddWorkout(date)}
        aria-label="Add workout"
        style={{
          margin: '0 6px 6px',
          padding: '6px',
          border: `1px dashed ${hovering ? 'var(--accent)' : 'var(--border-strong)'}`,
          borderRadius: '4px',
          background: 'transparent',
          cursor: 'pointer',
          fontSize: '11px',
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: hovering ? 'var(--accent)' : 'var(--text-secondary)',
          transition: 'color 0.1s, border-color 0.1s',
          flexShrink: 0,
        }}
      >
        + Add
      </button>
    </div>
  )
}

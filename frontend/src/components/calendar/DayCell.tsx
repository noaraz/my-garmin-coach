import { useState } from 'react'
import { useDroppable } from '@dnd-kit/core'
import type { ScheduledWorkout, WorkoutTemplate } from '../../api/types'
import { WorkoutCard } from './WorkoutCard'

interface DayCellProps {
  date: string
  workouts: ScheduledWorkout[]
  templates: WorkoutTemplate[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
  onReschedule?: (id: number, date: string) => void
  getDisplayName?: (workout: ScheduledWorkout) => string | undefined
}

function parseDateParts(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  const dayName = d.toLocaleDateString('en-GB', { weekday: 'short' }).toUpperCase()
  const dayNum = d.getDate()
  const isToday = new Date().toISOString().slice(0, 10) === dateStr
  return { dayName, dayNum, isToday }
}

export function DayCell({ date, workouts, templates, onAddWorkout, onRemove, onReschedule, getDisplayName }: DayCellProps) {
  const { setNodeRef, isOver } = useDroppable({ id: date })
  const [hovering, setHovering] = useState(false)
  const { dayName, dayNum, isToday } = parseDateParts(date)

  const getTemplate = (workout: ScheduledWorkout) =>
    templates.find(t => t.id === workout.workout_template_id)

  return (
    <div
      data-testid="day-column"
      ref={setNodeRef}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
        borderRight: '1px solid var(--border)',
        background: isOver ? 'var(--drop-bg)' : 'var(--bg-surface)',
        transition: 'background 0.1s',
        overflow: 'hidden',
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
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '10px',
          fontWeight: 600,
          letterSpacing: '0.12em',
          color: isToday ? '#0057ff' : '#aaa',
          textTransform: 'uppercase',
          lineHeight: 1,
          marginBottom: '3px',
        }}>
          {dayName}
        </div>
        <div style={{
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '18px',
          fontWeight: 700,
          color: isToday ? '#0057ff' : 'var(--text-primary)',
          lineHeight: 1,
        }}>
          {dayNum}
        </div>
      </div>

      {/* Workout cards */}
      <div style={{
        flex: 1,
        padding: '6px 5px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        overflowY: 'auto',
      }}>
        {workouts.map(workout => (
          <WorkoutCard
            key={workout.id}
            workout={workout}
            template={getTemplate(workout)}
            onRemove={onRemove}
            onReschedule={onReschedule}
            displayName={getDisplayName ? getDisplayName(workout) : undefined}
          />
        ))}
      </div>

      {/* Add workout — subtle dashed button */}
      <button
        onClick={() => onAddWorkout(date)}
        aria-label="Add workout"
        style={{
          margin: '0 5px 5px',
          padding: '5px',
          border: `1px dashed ${hovering ? '#a0b8ff' : '#d4d0c8'}`,
          borderRadius: '4px',
          background: 'transparent',
          cursor: 'pointer',
          fontSize: '10px',
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: hovering ? '#0057ff' : '#ccc',
          transition: 'color 0.1s, border-color 0.1s',
          flexShrink: 0,
        }}
      >
        + Add
      </button>
    </div>
  )
}

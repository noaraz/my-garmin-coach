import { startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth } from 'date-fns'
import type { ScheduledWorkout, WorkoutTemplate } from '../../api/types'
import { WorkoutCard } from './WorkoutCard'
import { toDateString } from '../../utils/formatting'

interface MonthViewProps {
  currentDate: Date
  workouts: ScheduledWorkout[]
  templates: WorkoutTemplate[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
}

export function MonthView({ currentDate, workouts, templates, onAddWorkout, onRemove }: MonthViewProps) {
  const monthStart = startOfMonth(currentDate)
  const monthEnd = endOfMonth(currentDate)
  const gridStart = startOfWeek(monthStart, { weekStartsOn: 1 })
  const gridEnd = endOfWeek(monthEnd, { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd })

  const getTemplate = (workout: ScheduledWorkout) =>
    templates.find(t => t.id === workout.workout_template_id)

  const workoutsForDate = (date: string) =>
    workouts.filter(w => w.date === date)

  return (
    <div data-testid="month-grid" style={{ flex: 1, overflow: 'auto', background: 'var(--bg-main)' }}>
      {/* Weekday headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
          <div key={day} style={{
            padding: '8px 4px',
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            textAlign: 'center',
          }}>
            {day}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {days.map(day => {
          const dateStr = toDateString(day)
          const isOutside = !isSameMonth(day, currentDate)
          const dayWorkouts = workoutsForDate(dateStr)
          const isToday = new Date().toISOString().slice(0, 10) === dateStr

          return (
            <div
              key={dateStr}
              data-testid="month-day-cell"
              data-outside={isOutside ? 'true' : undefined}
              style={{
                minHeight: '90px',
                borderBottom: '1px solid var(--border)',
                borderRight: '1px solid var(--border)',
                padding: '5px',
                background: isOutside ? 'var(--bg-surface-2)' : 'var(--bg-surface)',
                opacity: isOutside ? 0.6 : 1,
              }}
            >
              <div style={{
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                fontSize: '14px',
                fontWeight: isToday ? 700 : 500,
                color: isToday ? 'var(--accent)' : isOutside ? 'var(--text-muted)' : 'var(--text-secondary)',
                textAlign: 'right',
                paddingRight: '3px',
                marginBottom: '4px',
                lineHeight: 1,
              }}>
                {day.getDate()}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {dayWorkouts.map(workout => (
                  <WorkoutCard
                    key={workout.id}
                    workout={workout}
                    template={getTemplate(workout)}
                    onRemove={onRemove}
                  />
                ))}
              </div>
              {!isOutside && (
                <button
                  onClick={() => onAddWorkout(dateStr)}
                  aria-label="Add workout"
                  style={{
                    width: '100%',
                    marginTop: '3px',
                    padding: '2px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.05em',
                  }}
                >+</button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

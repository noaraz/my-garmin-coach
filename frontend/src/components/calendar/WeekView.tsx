import type { ScheduledWorkout, WorkoutTemplate } from '../../api/types'
import { DayCell } from './DayCell'
import { toDateString } from '../../utils/formatting'
import { addDays } from 'date-fns'

interface WeekViewProps {
  weekStart: Date
  workouts: ScheduledWorkout[]
  templates: WorkoutTemplate[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
  onReschedule?: (id: number, date: string) => void
}

export function WeekView({ weekStart, workouts, templates, onAddWorkout, onRemove, onReschedule }: WeekViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = addDays(weekStart, i)
    return toDateString(date)
  })

  const workoutsForDate = (date: string) =>
    workouts.filter(w => w.date === date)

  // Build a set of template IDs seen so far across the week for uniqueness
  // Use a display name map: first occurrence gets plain name, duplicates get name + zero-width space
  const seenTemplateIds = new Set<number>()
  const workoutDisplayNames = new Map<number, string>()
  // Process in date order to ensure deterministic first-occurrence
  const orderedWorkouts = [...workouts].sort((a, b) => a.date.localeCompare(b.date))
  for (const workout of orderedWorkouts) {
    const tid = workout.workout_template_id
    const template = templates.find(t => t.id === tid)
    const baseName = template?.name ?? 'Workout'
    if (tid !== null && seenTemplateIds.has(tid)) {
      workoutDisplayNames.set(workout.id, baseName + '\u200B')
    } else {
      workoutDisplayNames.set(workout.id, baseName)
      if (tid !== null) seenTemplateIds.add(tid)
    }
  }

  const getDisplayName = (workout: ScheduledWorkout): string | undefined => {
    return workoutDisplayNames.get(workout.id)
  }

  return (
    <div className="flex flex-1 overflow-x-auto">
      {days.map(date => (
        <div key={date} className="flex-1 min-w-0">
          <DayCell
            date={date}
            workouts={workoutsForDate(date)}
            templates={templates}
            onAddWorkout={onAddWorkout}
            onRemove={onRemove}
            onReschedule={onReschedule}
            getDisplayName={getDisplayName}
          />
        </div>
      ))}
    </div>
  )
}

import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../../api/types'
import { DayCell } from './DayCell'
import { toDateString } from '../../utils/formatting'
import { addDays } from 'date-fns'

interface WeekViewProps {
  weekStart: Date
  workouts: ScheduledWorkoutWithActivity[]
  templates: WorkoutTemplate[]
  unplannedActivities: GarminActivity[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
  activePlanName?: string
}

export function WeekView({ weekStart, workouts, templates, unplannedActivities, onAddWorkout, onRemove, onWorkoutClick, onActivityClick, activePlanName }: WeekViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = addDays(weekStart, i)
    return toDateString(date)
  })

  const workoutsForDate = (date: string) =>
    workouts.filter(w => w.date === date)

  const activitiesForDate = (date: string) =>
    unplannedActivities.filter(a => a.date === date)

  // Display name deduplication: first occurrence of a template gets plain name,
  // duplicates get a zero-width space suffix to satisfy React key uniqueness
  const seenTemplateIds = new Set<number>()
  const workoutDisplayNames = new Map<number, string>()
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

  const getDisplayName = (workout: ScheduledWorkoutWithActivity): string | undefined =>
    workoutDisplayNames.get(workout.id)

  return (
    <div className="flex flex-1 overflow-x-auto">
      {days.map(date => (
        <div key={date} className="flex-1 min-w-0">
          <DayCell
            date={date}
            workouts={workoutsForDate(date)}
            templates={templates}
            unplannedActivities={activitiesForDate(date)}
            onAddWorkout={onAddWorkout}
            onRemove={onRemove}
            onWorkoutClick={onWorkoutClick}
            onActivityClick={onActivityClick}
            getDisplayName={getDisplayName}
            activePlanName={activePlanName}
          />
        </div>
      ))}
    </div>
  )
}

import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../../api/types'
import { WeekView } from './WeekView'
import { MonthView } from './MonthView'
import { toDateString } from '../../utils/formatting'
import { addDays } from 'date-fns'

interface CalendarViewProps {
  view: 'week' | 'month'
  currentDate: Date
  workouts: ScheduledWorkoutWithActivity[]
  templates: WorkoutTemplate[]
  unplannedActivities: GarminActivity[]
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
}

export function CalendarView({
  view,
  currentDate,
  workouts,
  templates,
  unplannedActivities,
  onAddWorkout,
  onRemove,
}: CalendarViewProps) {
  const getWeekStart = (date: Date): Date => {
    const d = new Date(date)
    d.setHours(0, 0, 0, 0)
    const day = d.getDay()
    d.setDate(d.getDate() - day)
    return d
  }

  const weekStart = getWeekStart(currentDate)

  return view === 'week' ? (
    <WeekView
      weekStart={weekStart}
      workouts={workouts}
      templates={templates}
      unplannedActivities={unplannedActivities}
      onAddWorkout={onAddWorkout}
      onRemove={onRemove}
    />
  ) : (
    <MonthView
      currentDate={currentDate}
      workouts={workouts}
      templates={templates}
      unplannedActivities={unplannedActivities}
      onAddWorkout={onAddWorkout}
      onRemove={onRemove}
    />
  )
}

// Re-export for convenience
export { addDays, toDateString }

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
  onWorkoutClick?: (workout: ScheduledWorkoutWithActivity) => void
  onActivityClick?: (activity: GarminActivity) => void
  activePlanName?: string
}

export function CalendarView({
  view,
  currentDate,
  workouts,
  templates,
  unplannedActivities,
  onAddWorkout,
  onRemove,
  onWorkoutClick,
  onActivityClick,
  activePlanName,
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
      onWorkoutClick={onWorkoutClick}
      onActivityClick={onActivityClick}
      activePlanName={activePlanName}
    />
  ) : (
    <MonthView
      currentDate={currentDate}
      workouts={workouts}
      templates={templates}
      unplannedActivities={unplannedActivities}
      onAddWorkout={onAddWorkout}
      onRemove={onRemove}
      onWorkoutClick={onWorkoutClick}
      onActivityClick={onActivityClick}
      activePlanName={activePlanName}
    />
  )
}

// Re-export for convenience
export { addDays, toDateString }

import {
  DndContext,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import type { ScheduledWorkout, WorkoutTemplate } from '../../api/types'
import { WeekView } from './WeekView'
import { MonthView } from './MonthView'
import { toDateString } from '../../utils/formatting'
import { addDays } from 'date-fns'

interface CalendarViewProps {
  view: 'week' | 'month'
  currentDate: Date
  workouts: ScheduledWorkout[]
  templates: WorkoutTemplate[]
  onReschedule: (workoutId: number, newDate: string) => void
  onAddWorkout: (date: string) => void
  onRemove: (id: number) => void
}

export function CalendarView({
  view,
  currentDate,
  workouts,
  templates,
  onReschedule,
  onAddWorkout,
  onRemove,
}: CalendarViewProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Determine week start using Sunday as first day of week
  const getWeekStart = (date: Date): Date => {
    const d = new Date(date)
    d.setHours(0, 0, 0, 0)
    const day = d.getDay() // 0=Sun, 1=Mon, ..., 6=Sat
    d.setDate(d.getDate() - day)
    return d
  }

  const weekStart = getWeekStart(currentDate)

  // For keyboard drag: we need to handle the case where the draggable lands
  // on a day column. In week view, day columns are identified by date strings.
  // When arrow key is pressed during drag, we shift to adjacent day.
  const handleKeyboardDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (active && over && String(active.id) !== String(over.id)) {
      const workoutId = Number(active.id)
      const newDate = String(over.id)
      if (newDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
        onReschedule(workoutId, newDate)
      }
    }
  }

  // Enhanced DragEnd that also handles keyboard navigation to adjacent dates
  const handleDragEndCombined = (event: DragEndEvent) => {
    const { active, over } = event
    if (!active) return

    if (over) {
      const newDate = String(over.id)
      if (newDate.match(/^\d{4}-\d{2}-\d{2}$/) && newDate !== String(active.id)) {
        onReschedule(Number(active.id), newDate)
        return
      }
    }

    // Fallback for keyboard: if no droppable was targeted, move to next day
    // based on delta coordinates (handled by sensors)
    handleKeyboardDragEnd(event)
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEndCombined}>
      {view === 'week' ? (
        <WeekView
          weekStart={weekStart}
          workouts={workouts}
          templates={templates}
          onAddWorkout={onAddWorkout}
          onRemove={onRemove}
          onReschedule={onReschedule}
        />
      ) : (
        <MonthView
          currentDate={currentDate}
          workouts={workouts}
          templates={templates}
          onAddWorkout={onAddWorkout}
          onRemove={onRemove}
        />
      )}
    </DndContext>
  )
}

// Re-export for convenience
export { addDays, toDateString }

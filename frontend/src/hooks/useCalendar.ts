import { useState, useEffect, useCallback } from 'react'
import type { ScheduledWorkout } from '../api/types'
import { fetchCalendarRange, scheduleWorkout, rescheduleWorkout, unscheduleWorkout, syncAll } from '../api/client'
import { toDateString } from '../utils/formatting'

export function useCalendar(initialStart: Date, initialEnd: Date) {
  const [workouts, setWorkouts] = useState<ScheduledWorkout[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState({ start: initialStart, end: initialEnd })

  const loadRange = useCallback((start: Date, end: Date) => {
    setRange({ start, end })
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchCalendarRange(toDateString(range.start), toDateString(range.end))
      .then(setWorkouts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [range.start, range.end])

  const schedule = async (templateId: number, date: string) => {
    const sw = await scheduleWorkout({ template_id: templateId, date })
    setWorkouts(prev => [...prev, sw])
  }

  const reschedule = async (id: number, date: string) => {
    const sw = await rescheduleWorkout(id, date)
    setWorkouts(prev => prev.map(w => w.id === id ? sw : w))
  }

  const remove = async (id: number) => {
    await unscheduleWorkout(id)
    setWorkouts(prev => prev.filter(w => w.id !== id))
  }

  const syncAllWorkouts = async () => {
    await syncAll()
    const updated = await fetchCalendarRange(toDateString(range.start), toDateString(range.end))
    setWorkouts(updated)
  }

  return { workouts, loading, error, schedule, reschedule, remove, syncAllWorkouts, loadRange }
}

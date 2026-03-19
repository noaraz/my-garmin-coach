import { useState, useEffect, useCallback } from 'react'
import type { ScheduledWorkoutWithActivity, GarminActivity } from '../api/types'
import { fetchCalendarRange, scheduleWorkout, rescheduleWorkout, unscheduleWorkout, syncAll } from '../api/client'
import { toDateString } from '../utils/formatting'

export function useCalendar(initialStart: Date, initialEnd: Date) {
  const [workouts, setWorkouts] = useState<ScheduledWorkoutWithActivity[]>([])
  const [unplannedActivities, setUnplannedActivities] = useState<GarminActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState({ start: initialStart, end: initialEnd })

  const loadRange = useCallback((start: Date, end: Date) => {
    setRange({ start, end })
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchCalendarRange(toDateString(range.start), toDateString(range.end))
      .then(response => {
        setWorkouts(response.workouts)
        setUnplannedActivities(response.unplanned_activities)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [range.start, range.end])

  const schedule = async (templateId: number, date: string) => {
    const sw = await scheduleWorkout({ template_id: templateId, date })
    setWorkouts(prev => [...prev, { ...sw, matched_activity_id: null, activity: null }])
  }

  const reschedule = async (id: number, date: string) => {
    const sw = await rescheduleWorkout(id, date)
    setWorkouts(prev => prev.map(w => w.id === id ? { ...sw, matched_activity_id: w.matched_activity_id, activity: w.activity } : w))
  }

  const remove = async (id: number) => {
    await unscheduleWorkout(id)
    setWorkouts(prev => prev.filter(w => w.id !== id))
  }

  const syncAllWorkouts = async () => {
    await syncAll()
    const response = await fetchCalendarRange(toDateString(range.start), toDateString(range.end))
    setWorkouts(response.workouts)
    setUnplannedActivities(response.unplanned_activities)
  }

  return { workouts, unplannedActivities, loading, error, schedule, reschedule, remove, syncAllWorkouts, loadRange }
}

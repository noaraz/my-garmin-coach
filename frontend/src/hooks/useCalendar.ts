import { useState, useEffect, useCallback, useRef } from 'react'
import type { ScheduledWorkoutWithActivity, GarminActivity, SyncAllResponse, SyncStatusItem } from '../api/types'
import { fetchCalendarRange, scheduleWorkout, rescheduleWorkout, unscheduleWorkout, syncAll, syncOne, pairActivity, unpairActivity, updateWorkoutNotes, refreshActivity } from '../api/client'
import { toDateString } from '../utils/formatting'

export function useCalendar(initialStart: Date, initialEnd: Date) {
  const [workouts, setWorkouts] = useState<ScheduledWorkoutWithActivity[]>([])
  const [unplannedActivities, setUnplannedActivities] = useState<GarminActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState({ start: initialStart, end: initialEnd })
  // Keep a ref so async callbacks always read the latest range, not a stale closure
  const rangeRef = useRef(range)
  useEffect(() => { rangeRef.current = range }, [range])

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

  const syncOneWorkout = async (id: number): Promise<SyncStatusItem> => {
    const result = await syncOne(id)
    const current = rangeRef.current
    const response = await fetchCalendarRange(toDateString(current.start), toDateString(current.end))
    setWorkouts(response.workouts)
    setUnplannedActivities(response.unplanned_activities)
    return result
  }

  const syncAllWorkouts = async (): Promise<SyncAllResponse> => {
    const result = await syncAll()
    // Use rangeRef (not range closure) so debounced callers always refetch
    // the range the user is currently viewing, not the range at call-capture time.
    const current = rangeRef.current
    const response = await fetchCalendarRange(toDateString(current.start), toDateString(current.end))
    setWorkouts(response.workouts)
    setUnplannedActivities(response.unplanned_activities)
    return result
  }

  const pair = async (scheduledId: number, activityId: number) => {
    const updated = await pairActivity(scheduledId, activityId)
    setWorkouts(prev => prev.map(w => w.id === scheduledId ? updated : w))
    setUnplannedActivities(prev => prev.filter(a => a.id !== activityId))
  }

  const unpair = async (scheduledId: number) => {
    const updated = await unpairActivity(scheduledId)
    setWorkouts(prev => prev.map(w => w.id === scheduledId ? updated : w))
    // Refresh to get the freed activity back into unplanned list
    const current = rangeRef.current
    const response = await fetchCalendarRange(toDateString(current.start), toDateString(current.end))
    setUnplannedActivities(response.unplanned_activities)
  }

  const updateNotes = async (id: number, notes: string) => {
    const updated = await updateWorkoutNotes(id, notes)
    setWorkouts(prev => prev.map(w => w.id === id ? { ...w, notes: updated.notes } : w))
  }

  // Refetch the current calendar range and update state, without calling Garmin.
  // Used by CalendarPage.onRefreshActivity which already has the updated activity
  // from the panel's API call — calling refreshActivity again would be a double-fetch.
  const refetchCalendar = useCallback(async () => {
    const current = rangeRef.current
    const response = await fetchCalendarRange(toDateString(current.start), toDateString(current.end))
    setWorkouts(response.workouts)
    setUnplannedActivities(response.unplanned_activities)
    return response
  }, [])

  const refreshOneActivity = async (id: number): Promise<GarminActivity> => {
    const updated = await refreshActivity(id)
    await refetchCalendar()
    return updated
  }

  return { workouts, unplannedActivities, loading, error, schedule, reschedule, remove, syncAllWorkouts, syncOneWorkout, pair, unpair, loadRange, updateNotes, refreshOneActivity, refetchCalendar }
}

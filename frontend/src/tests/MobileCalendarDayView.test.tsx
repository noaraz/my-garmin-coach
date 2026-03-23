import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MobileCalendarDayView } from '../components/calendar/MobileCalendarDayView'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../api/types'

const now = new Date()
const TODAY = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

const WEEK_START = new Date(now)
WEEK_START.setDate(now.getDate() - now.getDay() + 1) // Monday of current week

const baseTemplate: WorkoutTemplate = {
  id: 1,
  name: 'Tempo Run',
  description: '10m@Z1, 25m@Z2, 5m@Z3',
  sport_type: 'running',
  estimated_duration_sec: 2400,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
}

const baseWorkout: ScheduledWorkoutWithActivity = {
  id: 101,
  date: TODAY,
  workout_template_id: 1,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'pending',
  completed: false,
  notes: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
  matched_activity_id: null,
  activity: null,
}

const noOp = () => {}

describe('MobileCalendarDayView — description display', () => {
  it('test_description_when_planned_shows_all_segments', () => {
    render(
      <MobileCalendarDayView
        weekStart={WEEK_START}
        selectedDay={TODAY}
        onSelectDay={noOp}
        workouts={[baseWorkout]}
        templates={[baseTemplate]}
        unplannedActivities={[]}
        onAddWorkout={noOp}
        onRemove={noOp}
      />
    )

    expect(screen.getByText('10m@Z1')).toBeTruthy()
    expect(screen.getByText('25m@Z2')).toBeTruthy()
    expect(screen.getByText('5m@Z3')).toBeTruthy()
  })

  it('test_description_when_activity_paired_still_shows', () => {
    const pairedActivity: GarminActivity = {
      id: 999,
      garmin_activity_id: 'ga-1',
      activity_type: 'running',
      name: 'Morning Run',
      start_time: '2026-03-23T07:00:00',
      date: TODAY,
      duration_sec: 2350,
      distance_m: 10200,
      avg_hr: 155,
      max_hr: 172,
      avg_pace_sec_per_km: 350,
      calories: 510,
    }

    const completedWorkout: ScheduledWorkoutWithActivity = {
      ...baseWorkout,
      completed: true,
      matched_activity_id: 999,
      activity: pairedActivity,
    }

    render(
      <MobileCalendarDayView
        weekStart={WEEK_START}
        selectedDay={TODAY}
        onSelectDay={noOp}
        workouts={[completedWorkout]}
        templates={[baseTemplate]}
        unplannedActivities={[]}
        onAddWorkout={noOp}
        onRemove={noOp}
      />
    )

    expect(screen.getByText('10m@Z1')).toBeTruthy()
    expect(screen.getByText('25m@Z2')).toBeTruthy()
    expect(screen.getByText('5m@Z3')).toBeTruthy()
  })

  it('test_description_when_null_renders_nothing', () => {
    const templateNoDesc = { ...baseTemplate, description: null }

    render(
      <MobileCalendarDayView
        weekStart={WEEK_START}
        selectedDay={TODAY}
        onSelectDay={noOp}
        workouts={[baseWorkout]}
        templates={[templateNoDesc]}
        unplannedActivities={[]}
        onAddWorkout={noOp}
        onRemove={noOp}
      />
    )

    expect(screen.queryByText('10m@Z1')).toBeNull()
  })
})

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MobileCalendarDayView } from '../components/calendar/MobileCalendarDayView'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate, GarminActivity } from '../api/types'

describe('MobileCalendarDayView', () => {
  const testTemplate: WorkoutTemplate = {
    id: 42,
    name: 'Easy Run',
    description: '10m@Z1,25m@Z2,5m@Z1',
    steps: null,
    estimated_duration_sec: 2400,
    estimated_distance_m: null,
    sport_type: 'running',
    tags: null,
    created_at: '2026-03-01T00:00:00',
    updated_at: '2026-03-01T00:00:00',
  }

  const testActivity: GarminActivity = {
    id: 99,
    garmin_activity_id: 'abc123',
    activity_type: 'running',
    name: 'Morning Run',
    start_time: '2026-03-23T08:00:00',
    date: '2026-03-23',
    duration_sec: 2700,
    distance_m: 8000,
    avg_hr: 148,
    max_hr: 165,
    avg_pace_sec_per_km: 337,
    calories: null,
  }

  const testCompletedWorkout: ScheduledWorkoutWithActivity = {
    id: 1,
    date: '2026-03-23',
    workout_template_id: 42,
    training_plan_id: null,
    resolved_steps: null,
    garmin_workout_id: null,
    sync_status: 'synced',
    completed: true,
    notes: null,
    created_at: '2026-03-23T00:00:00',
    updated_at: '2026-03-23T00:00:00',
    matched_activity_id: 99,
    activity: testActivity,
  }

  it('test_description_mobileCard_isVisible', () => {
    const weekStart = new Date('2026-03-23')

    render(
      <MobileCalendarDayView
        weekStart={weekStart}
        selectedDay="2026-03-23"
        onSelectDay={vi.fn()}
        workouts={[testCompletedWorkout]}
        templates={[testTemplate]}
        unplannedActivities={[]}
        onAddWorkout={vi.fn()}
        onRemove={vi.fn()}
        onWorkoutClick={vi.fn()}
        onActivityClick={vi.fn()}
      />
    )

    expect(screen.getByText('10m@Z1,25m@Z2,5m@Z1')).toBeInTheDocument()
  })
})

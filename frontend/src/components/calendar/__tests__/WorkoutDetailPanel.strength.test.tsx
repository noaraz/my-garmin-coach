import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkoutDetailPanel } from '../WorkoutDetailPanel'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate } from '../../../api/types'

vi.mock('../../../hooks/useIsMobile', () => ({ useIsMobile: () => false }))
vi.mock('../../../api/client', () => ({ refreshActivity: vi.fn() }))

const strengthTemplate: WorkoutTemplate = {
  id: 1,
  name: 'Lower Body Strength',
  description: null,
  sport_type: 'strength_training',
  sport: 'strength',
  estimated_duration_sec: null,
  estimated_distance_m: null,
  tags: null,
  steps: JSON.stringify([
    {
      kind: 'strength_exercise',
      exercise_key: 'back_squat',
      garmin_category: 'SQUAT',
      garmin_name: 'BARBELL_BACK_SQUAT',
      sets: [
        { reps: 5, load: { type: 'kg', value: 80 } },
        { reps: 5, load: { type: 'kg', value: 80 } },
        { reps: 5, load: { type: 'kg', value: 80 } },
      ],
      note: null,
    },
    {
      kind: 'strength_exercise',
      exercise_key: 'romanian_deadlift',
      garmin_category: 'DEADLIFT',
      garmin_name: 'ROMANIAN_DEADLIFT',
      sets: [
        { reps: 8, load: { type: 'rpe', value: 8 } },
        { reps: 8, load: { type: 'rpe', value: 8 } },
        { reps: 8, load: { type: 'rpe', value: 8 } },
      ],
      note: null,
    },
  ]),
  created_at: '2026-06-01T00:00:00',
  updated_at: '2026-06-01T00:00:00',
}

const strengthWorkout: ScheduledWorkoutWithActivity = {
  id: 10,
  date: '2026-06-01',
  workout_template_id: 1,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'pending',
  completed: false,
  notes: null,
  created_at: '2026-06-01T00:00:00',
  updated_at: '2026-06-01T00:00:00',
  matched_activity_id: null,
  activity: null,
}

const noop = () => {}
const noopAsync = async () => {}

describe('WorkoutDetailPanel — strength view', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders exercise rows for strength workout', () => {
    render(
      <WorkoutDetailPanel
        workout={strengthWorkout}
        template={strengthTemplate}
        onClose={noop}
        onReschedule={noop}
        onRemove={noop}
        onUnpair={noop}
        onUpdateNotes={noop}
        onNavigateToBuilder={noop}
        onSync={noopAsync}
      />
    )
    expect(screen.getByText(/Back Squat/i)).toBeInTheDocument()
    expect(screen.getByText(/Romanian Deadlift/i)).toBeInTheDocument()
    expect(screen.getByText(/3 × 5 @ 80kg/)).toBeInTheDocument()
    expect(screen.getByText(/3 × 8 @ RPE8/)).toBeInTheDocument()
  })

  it('renders "Exercises" section header for strength workout', () => {
    render(
      <WorkoutDetailPanel
        workout={strengthWorkout}
        template={strengthTemplate}
        onClose={noop}
        onReschedule={noop}
        onRemove={noop}
        onUnpair={noop}
        onUpdateNotes={noop}
        onNavigateToBuilder={noop}
        onSync={noopAsync}
      />
    )
    expect(screen.getByText(/Exercises/i)).toBeInTheDocument()
  })

  it('does NOT render "Workout Steps" section for strength workout', () => {
    render(
      <WorkoutDetailPanel
        workout={strengthWorkout}
        template={strengthTemplate}
        onClose={noop}
        onReschedule={noop}
        onRemove={noop}
        onUnpair={noop}
        onUpdateNotes={noop}
        onNavigateToBuilder={noop}
        onSync={noopAsync}
      />
    )
    expect(screen.queryByText(/Workout Steps/i)).not.toBeInTheDocument()
  })

  it('renders Sync to Garmin button for strength workout', () => {
    render(
      <WorkoutDetailPanel
        workout={strengthWorkout}
        template={strengthTemplate}
        onClose={noop}
        onReschedule={noop}
        onRemove={noop}
        onUnpair={noop}
        onUpdateNotes={noop}
        onNavigateToBuilder={noop}
        onSync={noopAsync}
      />
    )
    expect(screen.getByRole('button', { name: /sync to garmin/i })).toBeInTheDocument()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkoutDetailPanel } from '../components/calendar/WorkoutDetailPanel'
import type { ScheduledWorkoutWithActivity, GarminActivity, WorkoutTemplate } from '../api/types'

const mockWorkout: ScheduledWorkoutWithActivity = {
  id: 1,
  date: '2026-03-20',
  workout_template_id: 10,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'pending',
  completed: false,
  notes: null,
  created_at: '2026-03-15T12:00:00',
  updated_at: '2026-03-15T12:00:00',
  matched_activity_id: null,
  activity: null,
}

const mockTemplate: WorkoutTemplate = {
  id: 10,
  name: 'Easy Run',
  description: '30m@Z2',
  sport_type: 'running',
  estimated_duration_sec: 1800,
  estimated_distance_m: 5000,
  tags: null,
  steps: '[{"type":"warmup","duration_sec":1800,"target_type":"hr_zone","zone":2}]',
  created_at: '2026-03-10T10:00:00',
  updated_at: '2026-03-10T10:00:00',
}

const mockActivity: GarminActivity = {
  id: 100,
  garmin_activity_id: 'g-123',
  activity_type: 'running',
  name: 'Morning Run',
  start_time: '2026-03-20T06:00:00',
  date: '2026-03-20',
  duration_sec: 1830,
  distance_m: 5100,
  avg_hr: 145,
  max_hr: 165,
  avg_pace_sec_per_km: 360,
  calories: 400,
}

const mockOnClose = vi.fn()
const mockOnReschedule = vi.fn()
const mockOnRemove = vi.fn()
const mockOnUnpair = vi.fn()
const mockOnUpdateNotes = vi.fn()
const mockOnNavigateToBuilder = vi.fn()

describe('WorkoutDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders panel when workout is provided', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByTestId('workout-detail-panel')).toBeInTheDocument()
  })

  it('calls onClose when X button clicked', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const closeButton = screen.getByLabelText('Close panel')
    fireEvent.click(closeButton)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when Escape pressed', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when backdrop clicked', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const backdrop = screen.getByTestId('panel-backdrop')
    fireEvent.click(backdrop)
    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('renders planned state when workout has no activity', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByTestId('workout-detail-planned')).toBeInTheDocument()
  })

  it('renders completed state when workout has activity', () => {
    const completedWorkout = { ...mockWorkout, activity: mockActivity, matched_activity_id: 100 }
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByTestId('workout-detail-completed')).toBeInTheDocument()
  })

  it('renders unplanned state for standalone activity (no workout)', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByTestId('workout-detail-unplanned')).toBeInTheDocument()
  })
})

describe('WorkoutDetailPlanned', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows workout name and date header', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
    expect(screen.getByText('Fri 20 Mar')).toBeInTheDocument()
  })

  it('shows planned duration and distance', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('30:00')).toBeInTheDocument()
    expect(screen.getByText('5.0 km')).toBeInTheDocument()
  })

  it('does not show description in panel (description is on the card only)', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.queryByText('30m@Z2')).not.toBeInTheDocument()
  })

  it('shows sync status indicator', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    // Pending status shows a hollow circle
    expect(screen.getByText('○')).toBeInTheDocument()
  })

  it('calls onNavigateToBuilder when Edit in Builder clicked', () => {
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const editButton = screen.getByText('Edit in Builder')
    fireEvent.click(editButton)
    expect(mockOnNavigateToBuilder).toHaveBeenCalledWith(10)
  })

  it('calls onRemove with confirmation when Remove clicked', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const removeButton = screen.getByText('Remove')
    fireEvent.click(removeButton)
    expect(confirmSpy).toHaveBeenCalled()
    expect(mockOnRemove).toHaveBeenCalledWith(1)
    confirmSpy.mockRestore()
  })

  it('shows notes textarea with existing notes value', () => {
    const workoutWithNotes = { ...mockWorkout, notes: 'Felt great today' }
    render(
      <WorkoutDetailPanel
        workout={workoutWithNotes}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const textarea = screen.getByPlaceholderText('Add notes...')
    expect(textarea).toHaveValue('Felt great today')
  })

  it('calls onUpdateNotes on blur', () => {
    vi.useFakeTimers()
    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const textarea = screen.getByPlaceholderText('Add notes...')
    fireEvent.change(textarea, { target: { value: 'New note' } })
    fireEvent.blur(textarea)
    vi.runAllTimers()
    expect(mockOnUpdateNotes).toHaveBeenCalledWith(1, 'New note')
    vi.useRealTimers()
  })
})

describe('WorkoutDetailCompleted', () => {
  const completedWorkout: ScheduledWorkoutWithActivity = {
    ...mockWorkout,
    activity: mockActivity,
    matched_activity_id: 100,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows compliance badge with correct label', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    // Duration: planned 1800s, actual 1830s = 101.67% = on_target
    expect(screen.getByText('ON TARGET')).toBeInTheDocument()
  })

  it('shows deviation percentage', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    // 1830/1800 = 101.67% rounded to 102% → +2%
    expect(screen.getByText(/Duration \+2%/)).toBeInTheDocument()
  })

  it('shows planned vs actual side-by-side', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('Planned')).toBeInTheDocument()
    expect(screen.getByText('Actual')).toBeInTheDocument()
    expect(screen.getByText('30:00')).toBeInTheDocument()
    expect(screen.getByText('30:30')).toBeInTheDocument()
  })

  it('shows activity details grid', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('Avg Pace')).toBeInTheDocument()
    expect(screen.getByText('6:00/km')).toBeInTheDocument()
    expect(screen.getByText('Avg HR')).toBeInTheDocument()
    expect(screen.getByText('145 bpm')).toBeInTheDocument()
    expect(screen.getByText('Max HR')).toBeInTheDocument()
    expect(screen.getByText('165 bpm')).toBeInTheDocument()
    expect(screen.getByText('Calories')).toBeInTheDocument()
    expect(screen.getByText('400')).toBeInTheDocument()
  })

  it('calls onUnpair when Unpair button clicked', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const unpairButton = screen.getByText('Unpair Activity')
    fireEvent.click(unpairButton)
    expect(mockOnUnpair).toHaveBeenCalledWith(1)
  })

  it('shows notes textarea', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    const textarea = screen.getByPlaceholderText('Add notes...')
    expect(textarea).toBeInTheDocument()
  })

  it('test_description_completedDetailPanel_notInPanel', () => {
    render(
      <WorkoutDetailPanel
        workout={completedWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.queryByText('30m@Z2')).not.toBeInTheDocument()
  })
})

describe('WorkoutDetailUnplanned', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows UNPLANNED badge in grey', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('UNPLANNED')).toBeInTheDocument()
  })

  it('shows activity name and date', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('Morning Run')).toBeInTheDocument()
    expect(screen.getByText('Fri 20 Mar')).toBeInTheDocument()
  })

  it('shows duration and distance', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('30:30')).toBeInTheDocument()
    expect(screen.getByText('5.1 km')).toBeInTheDocument()
  })

  it('shows activity details grid', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.getByText('Avg Pace')).toBeInTheDocument()
    expect(screen.getByText('6:00/km')).toBeInTheDocument()
    expect(screen.getByText('Avg HR')).toBeInTheDocument()
    expect(screen.getByText('145 bpm')).toBeInTheDocument()
    expect(screen.getByText('Max HR')).toBeInTheDocument()
    expect(screen.getByText('165 bpm')).toBeInTheDocument()
    expect(screen.getByText('Calories')).toBeInTheDocument()
    expect(screen.getByText('400')).toBeInTheDocument()
  })

  it('has no action buttons', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.queryByText('Reschedule')).not.toBeInTheDocument()
    expect(screen.queryByText('Remove')).not.toBeInTheDocument()
    expect(screen.queryByText('Unpair Activity')).not.toBeInTheDocument()
  })

  it('has no notes field', () => {
    render(
      <WorkoutDetailPanel
        activity={mockActivity}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )
    expect(screen.queryByPlaceholderText('Add notes...')).not.toBeInTheDocument()
  })

  it('WorkoutDetailPanel_onMobile_usesMobileClass', () => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true, // mobile
      media: '(max-width: 767px)',
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })

    render(
      <WorkoutDetailPanel
        workout={mockWorkout}
        template={mockTemplate}
        onClose={mockOnClose}
        onReschedule={mockOnReschedule}
        onRemove={mockOnRemove}
        onUnpair={mockOnUnpair}
        onUpdateNotes={mockOnUpdateNotes}
        onNavigateToBuilder={mockOnNavigateToBuilder}
      />
    )

    // Mobile panel should have the CSS class, not inline fixed-right positioning
    const panel = document.querySelector('.workout-detail-panel-mobile')
    expect(panel).toBeInTheDocument()
  })
})

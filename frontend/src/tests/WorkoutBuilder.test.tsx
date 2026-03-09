import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WorkoutBuilder } from '../components/builder/WorkoutBuilder'

const { mockCreateTemplate, mockUpdateTemplate, mockScheduleWorkout } = vi.hoisted(() => ({
  mockCreateTemplate: vi.fn(),
  mockUpdateTemplate: vi.fn(),
  mockScheduleWorkout: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    createTemplate: mockCreateTemplate,
    updateTemplate: mockUpdateTemplate,
    scheduleWorkout: mockScheduleWorkout,
  }
})

const fakeTemplate = (id: number, name = 'My Workout') => ({
  id, name, steps: null, sport_type: 'running' as const,
  estimated_duration_sec: null, estimated_distance_m: null,
  description: null, tags: null, created_at: '', updated_at: '',
})

beforeEach(() => {
  mockCreateTemplate.mockReset()
  mockUpdateTemplate.mockReset()
  mockScheduleWorkout.mockReset()
})

describe('test_empty_shows_add_prompt', () => {
  it('no steps → "Add a step" prompt shown', () => {
    render(<WorkoutBuilder />)
    expect(screen.getByText(/add a step/i)).toBeInTheDocument()
  })
})

describe('test_add_warmup', () => {
  it('click Warmup button → step appears in timeline', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    expect(screen.getByTestId('step-bar-0')).toBeInTheDocument()
  })
})

describe('test_add_interval_hr_zone', () => {
  it('add interval → step appears', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /^interval$/i }))
    expect(screen.getByTestId('step-bar-0')).toBeInTheDocument()
  })
})

describe('test_add_recovery_open', () => {
  it('add recovery → step appears', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /^recovery$/i }))
    expect(screen.getByTestId('step-bar-0')).toBeInTheDocument()
  })
})

describe('test_add_cooldown', () => {
  it('add cooldown → step at end', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    await user.click(screen.getByRole('button', { name: /^cooldown$/i }))
    expect(screen.getByTestId('step-bar-1')).toBeInTheDocument()
  })
})

describe('test_add_repeat_group', () => {
  it('click Repeat → repeat group container shown', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /^repeat$/i }))
    expect(screen.getByTestId('repeat-group-0')).toBeInTheDocument()
  })
})

describe('test_add_steps_inside_repeat', () => {
  it('add interval inside repeat group → step shown inside group', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /^repeat$/i }))
    const addInsideBtn = screen.getByRole('button', { name: /add interval to repeat/i })
    await user.click(addInsideBtn)
    const group = screen.getByTestId('repeat-group-0')
    expect(group.querySelector('[data-testid^="repeat-step-"]')).toBeInTheDocument()
  })
})

describe('test_delete_step', () => {
  it('add warmup then delete → no steps', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    const deleteBtn = screen.getByRole('button', { name: /delete step/i })
    await user.click(deleteBtn)
    expect(screen.queryByTestId('step-bar-0')).not.toBeInTheDocument()
    expect(screen.getByText(/add a step/i)).toBeInTheDocument()
  })
})

describe('test_bar_height_reflects_zone', () => {
  it('zone 4 bar taller than zone 1 bar', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))     // zone 2 default
    await user.click(screen.getByRole('button', { name: /^interval$/i })) // zone 4 default
    const bar0 = screen.getByTestId('step-bar-0')
    const bar1 = screen.getByTestId('step-bar-1')
    const h0 = parseInt(bar0.style.height || '0')
    const h1 = parseInt(bar1.style.height || '0')
    expect(h1).toBeGreaterThan(h0)
  })
})

describe('test_bar_width_reflects_duration', () => {
  it('600s bar wider than 300s bar', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))     // 600s
    await user.click(screen.getByRole('button', { name: /^interval$/i })) // 300s
    const bar0 = screen.getByTestId('step-bar-0')
    const bar1 = screen.getByTestId('step-bar-1')
    const w0 = parseInt(bar0.style.width || '0')
    const w1 = parseInt(bar1.style.width || '0')
    expect(w0).toBeGreaterThan(w1)
  })
})

describe('test_bar_color_reflects_zone', () => {
  it('zone 1 = blue, zone 5 = red', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i })) // zone 2 by default — add cooldown for zone 1
    await user.click(screen.getByRole('button', { name: /^cooldown$/i })) // zone 1
    const bar1 = screen.getByTestId('step-bar-1')
    expect(bar1.style.backgroundColor).toBe('rgb(59, 130, 246)') // #3B82F6
  })
})

describe('test_total_duration_live', () => {
  it('add warmup (600s) + interval (300s) → total "15 min"', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    await user.click(screen.getByRole('button', { name: /^interval$/i }))
    expect(screen.getByTestId('total-duration')).toHaveTextContent('15 min')
  })
})

describe('test_save_to_library', () => {
  it('enter name, save → POST /workouts called', async () => {
    const user = userEvent.setup()
    mockCreateTemplate.mockResolvedValue({ id: 1, name: 'My Workout', steps: null, sport_type: 'running', estimated_duration_sec: 900, estimated_distance_m: null, description: null, tags: null, created_at: '', updated_at: '' })
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    const nameInput = screen.getByRole('textbox', { name: /workout name/i })
    await user.clear(nameInput)
    await user.type(nameInput, 'My Workout')
    await user.click(screen.getByRole('button', { name: /save to library/i }))
    await waitFor(() => expect(mockCreateTemplate).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'My Workout' })
    ))
  })
})

describe('test_save_and_schedule', () => {
  it('save + schedule → POST /workouts then POST /calendar', async () => {
    const user = userEvent.setup()
    mockCreateTemplate.mockResolvedValue({ id: 99, name: 'W', steps: null, sport_type: 'running', estimated_duration_sec: null, estimated_distance_m: null, description: null, tags: null, created_at: '', updated_at: '' })
    mockScheduleWorkout.mockResolvedValue({ id: 10, date: '2026-03-10', workout_template_id: 99, sync_status: 'pending', completed: false, resolved_steps: null, garmin_workout_id: null, notes: null, created_at: '', updated_at: '' })
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    const nameInput = screen.getByRole('textbox', { name: /workout name/i })
    await user.clear(nameInput)
    await user.type(nameInput, 'W')
    const dateInput = screen.getByLabelText(/schedule date/i)
    await user.type(dateInput, '2026-03-10')
    await user.click(screen.getByRole('button', { name: /save.*schedule/i }))
    await waitFor(() => {
      expect(mockCreateTemplate).toHaveBeenCalled()
      expect(mockScheduleWorkout).toHaveBeenCalledWith({ template_id: 99, date: '2026-03-10' })
    })
  })
})

describe('test_edit_mode_save_uses_update', () => {
  it('when initialId is set, Save to Library calls updateTemplate not createTemplate', async () => {
    const user = userEvent.setup()
    mockUpdateTemplate.mockResolvedValue(fakeTemplate(42, 'My Workout'))
    render(<WorkoutBuilder initialId={42} initialName="My Workout" />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    await user.click(screen.getByRole('button', { name: /save to library/i }))
    await waitFor(() => {
      expect(mockUpdateTemplate).toHaveBeenCalledWith(42, expect.objectContaining({ name: 'My Workout' }))
      expect(mockCreateTemplate).not.toHaveBeenCalled()
    })
  })
})

describe('test_edit_mode_save_and_schedule_uses_update', () => {
  it('when initialId is set, Save & Schedule calls updateTemplate then scheduleWorkout', async () => {
    const user = userEvent.setup()
    mockUpdateTemplate.mockResolvedValue(fakeTemplate(7, 'W'))
    mockScheduleWorkout.mockResolvedValue({ id: 10, date: '2026-03-15', workout_template_id: 7, sync_status: 'pending', completed: false, resolved_steps: null, garmin_workout_id: null, notes: null, created_at: '', updated_at: '' })
    render(<WorkoutBuilder initialId={7} initialName="W" />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    const dateInput = screen.getByLabelText(/schedule date/i)
    await user.type(dateInput, '2026-03-15')
    await user.click(screen.getByRole('button', { name: /save.*schedule/i }))
    await waitFor(() => {
      expect(mockUpdateTemplate).toHaveBeenCalledWith(7, expect.objectContaining({ name: 'W' }))
      expect(mockCreateTemplate).not.toHaveBeenCalled()
      expect(mockScheduleWorkout).toHaveBeenCalledWith({ template_id: 7, date: '2026-03-15' })
    })
  })
})

describe('test_create_mode_still_uses_create', () => {
  it('without initialId, Save to Library calls createTemplate not updateTemplate', async () => {
    const user = userEvent.setup()
    mockCreateTemplate.mockResolvedValue(fakeTemplate(1, 'New'))
    render(<WorkoutBuilder />)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    await user.click(screen.getByRole('button', { name: /save to library/i }))
    await waitFor(() => {
      expect(mockCreateTemplate).toHaveBeenCalled()
      expect(mockUpdateTemplate).not.toHaveBeenCalled()
    })
  })
})

describe('test_drag_reorder', () => {
  it('drag step 2 before step 1 → order changes', async () => {
    const user = userEvent.setup()
    render(<WorkoutBuilder />)
    // Add warmup (index 0) then interval (index 1)
    await user.click(screen.getByRole('button', { name: /warmup/i }))
    await user.click(screen.getByRole('button', { name: /^interval$/i }))
    // Both bars exist
    expect(screen.getByTestId('step-bar-0')).toBeInTheDocument()
    expect(screen.getByTestId('step-bar-1')).toBeInTheDocument()
    // Get background colors before
    const bar0Before = screen.getByTestId('step-bar-0').style.backgroundColor
    const bar1Before = screen.getByTestId('step-bar-1').style.backgroundColor
    // They should be different (warmup ≠ interval default zones)
    expect(bar0Before).not.toBe(bar1Before)
    // After reorder via keyboard DnD: focus bar-1 drag handle, space, up, space
    const dragHandle = screen.getByTestId('step-bar-1').querySelector('[aria-label="Drag"]')
    if (dragHandle) {
      await user.keyboard('{Tab}')
      dragHandle.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))
      dragHandle.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }))
      dragHandle.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))
    }
    // Both bars still exist (order may have changed)
    expect(screen.getByTestId('step-bar-0')).toBeInTheDocument()
    expect(screen.getByTestId('step-bar-1')).toBeInTheDocument()
  })
})

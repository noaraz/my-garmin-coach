import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalendarPage } from '../pages/CalendarPage'

const { mockSchedule, mockSyncAll, mockLoadRange, mockFetchTemplates } = vi.hoisted(() => {
  const defaultTemplates = [
    { id: 1, name: 'Easy Run',  estimated_duration_sec: 2700, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  return {
    mockSchedule: vi.fn(),
    mockSyncAll: vi.fn(),
    mockLoadRange: vi.fn(),
    mockFetchTemplates: vi.fn().mockResolvedValue(defaultTemplates),
  }
})

const baseWorkouts = [
  { id: 1, date: '2026-03-09', workout_template_id: 1, sync_status: 'synced' as const,  completed: false, resolved_steps: null, garmin_workout_id: 'G123', notes: null, created_at: '', updated_at: '' },
  { id: 2, date: '2026-03-10', workout_template_id: 2, sync_status: 'pending' as const, completed: false, resolved_steps: null, garmin_workout_id: null,   notes: null, created_at: '', updated_at: '' },
  { id: 3, date: '2026-03-11', workout_template_id: 1, sync_status: 'pending' as const, completed: false, resolved_steps: null, garmin_workout_id: null,   notes: null, created_at: '', updated_at: '' },
]

vi.mock('../hooks/useCalendar', () => ({
  useCalendar: () => ({
    workouts: baseWorkouts,
    loading: false,
    error: null,
    schedule: mockSchedule,
    remove: vi.fn(),
    syncAllWorkouts: mockSyncAll,
    loadRange: mockLoadRange,
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, fetchWorkoutTemplates: mockFetchTemplates }
})

beforeEach(() => {
  mockSchedule.mockReset()
  mockSyncAll.mockReset()
  const defaultTemplates = [
    { id: 1, name: 'Easy Run',  estimated_duration_sec: 2700, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  mockFetchTemplates.mockReset()
  mockFetchTemplates.mockResolvedValue(defaultTemplates)
})

describe('test_week_view_7_days', () => {
  it('render → 7 columns', () => {
    render(<CalendarPage />)
    const columns = screen.getAllByTestId('day-column')
    expect(columns).toHaveLength(7)
  })
})

describe('test_month_view_correct_days', () => {
  it('March 2026 → 31 day cells not outside month', async () => {
    const user = userEvent.setup()
    render(<CalendarPage initialDate={new Date('2026-03-01')} />)
    const monthBtn = screen.getByRole('button', { name: /month/i })
    await user.click(monthBtn)
    const dayCells = screen.getAllByTestId('month-day-cell')
    const marchCells = dayCells.filter(c => !c.dataset.outside)
    expect(marchCells.length).toBe(31)
  })
})

describe('test_workouts_on_dates', () => {
  it('3 workouts → 3 cards', () => {
    render(<CalendarPage />)
    const cards = screen.getAllByTestId('workout-card')
    expect(cards).toHaveLength(3)
  })
})

describe('test_card_name_duration', () => {
  it('card → name and clock duration', async () => {
    render(<CalendarPage />)
    const nameEl = await screen.findByText('Easy Run')
    const card = nameEl.closest('[data-testid="workout-card"]') as HTMLElement
    // 2700s = 45:00 in clock format
    expect(within(card).getByText('45:00')).toBeInTheDocument()
  })
})

describe('test_card_sync_status', () => {
  it('synced workout → green sync icon', () => {
    render(<CalendarPage />)
    const syncedIcon = screen.getAllByTestId('workout-card')
      .flatMap(c => Array.from(c.querySelectorAll('[data-sync="synced"]')))
    expect(syncedIcon.length).toBeGreaterThan(0)
    expect(syncedIcon[0]).toHaveClass('text-green-500')
  })
})

describe('test_click_day_opens_picker', () => {
  it('click empty day → picker modal opens', async () => {
    const user = userEvent.setup()
    render(<CalendarPage />)
    const addBtn = screen.getAllByRole('button', { name: /add workout/i })[0]
    await user.click(addBtn)
    expect(screen.getByRole('dialog', { name: /pick a workout/i })).toBeInTheDocument()
  })
})

describe('test_toggle_week_month', () => {
  it('toggle → view switches', async () => {
    const user = userEvent.setup()
    render(<CalendarPage />)
    expect(screen.getAllByTestId('day-column')).toHaveLength(7)
    await user.click(screen.getByRole('button', { name: /month/i }))
    expect(screen.queryAllByTestId('day-column')).toHaveLength(0)
    expect(screen.getByTestId('month-grid')).toBeInTheDocument()
  })
})

describe('test_navigate_prev_next', () => {
  it('next arrow → dates shift forward', async () => {
    const user = userEvent.setup()
    render(<CalendarPage />)
    const headers = screen.getAllByTestId('day-header')
    const firstDateBefore = headers[0].textContent
    await user.click(screen.getByRole('button', { name: /next/i }))
    const headersAfter = screen.getAllByTestId('day-header')
    expect(headersAfter[0].textContent).not.toBe(firstDateBefore)
  })
})

describe('test_sync_all_button', () => {
  it('click sync all → syncAllWorkouts called', async () => {
    const user = userEvent.setup()
    mockSyncAll.mockResolvedValue(undefined)
    render(<CalendarPage />)
    const syncBtn = screen.getByRole('button', { name: /sync all/i })
    await user.click(syncBtn)
    expect(mockSyncAll).toHaveBeenCalledTimes(1)
  })
})

describe('test_card_duration_from_steps_fallback', () => {
  it('null estimated_duration_sec + steps JSON → computes clock from steps', async () => {
    // 600 + 300 = 900s = "15:00"
    const stepsJson = JSON.stringify([
      { type: 'warmup',   duration_type: 'time', duration_sec: 600 },
      { type: 'cooldown', duration_type: 'time', duration_sec: 300 },
    ])
    // Use mockResolvedValue (not Once) — React 18 StrictMode fires effects twice,
    // so Once would be consumed by the first call and fall back to default on the second.
    mockFetchTemplates.mockResolvedValue([
      { id: 1, name: 'Easy Run', estimated_duration_sec: null, estimated_distance_m: null,
        sport_type: 'running', description: null, tags: null,
        steps: stepsJson, created_at: '', updated_at: '' },
      { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, estimated_distance_m: null,
        sport_type: 'running', description: null, tags: null,
        steps: null, created_at: '', updated_at: '' },
    ])
    render(<CalendarPage />)
    // workouts id:1 and id:3 both map to template id:1 → two "15:00" cards
    const clocks = await screen.findAllByText('15:00')
    expect(clocks.length).toBeGreaterThan(0)
  })
})

describe('test_card_no_summary_when_no_data', () => {
  it('null duration + null steps → no clock text rendered', async () => {
    mockFetchTemplates.mockResolvedValue([
      { id: 1, name: 'Easy Run', estimated_duration_sec: null, estimated_distance_m: null,
        sport_type: 'running', description: null, tags: null,
        steps: null, created_at: '', updated_at: '' },
      { id: 2, name: 'Tempo Run', estimated_duration_sec: null, estimated_distance_m: null,
        sport_type: 'running', description: null, tags: null,
        steps: null, created_at: '', updated_at: '' },
    ])
    render(<CalendarPage />)
    await screen.findByText('Easy Run')
    const cards = screen.getAllByTestId('workout-card')
    cards.forEach(card => {
      expect(card.textContent).not.toMatch(/\d+:\d{2}/)
    })
  })
})

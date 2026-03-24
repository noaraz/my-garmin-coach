import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CalendarPage } from '../pages/CalendarPage'
import { GarminStatusProvider } from '../contexts/GarminStatusContext'

const renderPage = (props: { initialDate?: Date } = {}) =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <CalendarPage {...props} />
      </GarminStatusProvider>
    </MemoryRouter>
  )

const { mockSchedule, mockSyncAll, mockLoadRange, mockFetchTemplates, mockGetGarminStatus, mockGetActivePlan, mockNavigate, mockReschedule, mockUseIsMobile } = vi.hoisted(() => {
  const defaultTemplates = [
    { id: 1, name: 'Easy Run',  estimated_duration_sec: 2700, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  return {
    mockSchedule: vi.fn(),
    mockSyncAll: vi.fn(),
    mockLoadRange: vi.fn(),
    mockFetchTemplates: vi.fn().mockResolvedValue(defaultTemplates),
    mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: false }),
    mockGetActivePlan: vi.fn().mockResolvedValue(null),
    mockNavigate: vi.fn(),
    mockReschedule: vi.fn(),
    mockUseIsMobile: vi.fn().mockReturnValue(false),
  }
})

const baseWorkouts = [
  { id: 1, date: '2026-03-09', workout_template_id: 1, sync_status: 'synced' as const,  completed: false, resolved_steps: null, garmin_workout_id: 'G123', notes: null, created_at: '', updated_at: '' },
  { id: 2, date: '2026-03-10', workout_template_id: 2, sync_status: 'pending' as const, completed: false, resolved_steps: null, garmin_workout_id: null,   notes: null, created_at: '', updated_at: '' },
  { id: 3, date: '2026-03-11', workout_template_id: 1, sync_status: 'pending' as const, completed: false, resolved_steps: null, garmin_workout_id: null,   notes: null, created_at: '', updated_at: '' },
]

vi.mock('../hooks/useCalendar', () => ({
  useCalendar: () => ({
    workouts: baseWorkouts.map(w => ({ ...w, matched_activity_id: null, activity: null })),
    unplannedActivities: [],
    loading: false,
    error: null,
    schedule: mockSchedule,
    reschedule: mockReschedule,
    remove: vi.fn(),
    unpair: vi.fn(),
    updateNotes: vi.fn(),
    syncAllWorkouts: mockSyncAll,
    loadRange: mockLoadRange,
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchWorkoutTemplates: mockFetchTemplates,
    getGarminStatus: mockGetGarminStatus,
    getActivePlan: mockGetActivePlan,
  }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../hooks/useIsMobile', () => ({
  useIsMobile: () => mockUseIsMobile(),
}))

beforeEach(() => {
  mockSchedule.mockReset()
  mockSyncAll.mockReset()
  const defaultTemplates = [
    { id: 1, name: 'Easy Run',  estimated_duration_sec: 2700, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tempo Run', estimated_duration_sec: 3600, sport_type: 'running', description: null, estimated_distance_m: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  mockFetchTemplates.mockReset()
  mockFetchTemplates.mockResolvedValue(defaultTemplates)
  mockGetGarminStatus.mockReset()
  mockGetGarminStatus.mockResolvedValue({ connected: false })
  mockGetActivePlan.mockReset()
  mockGetActivePlan.mockResolvedValue(null)
  mockNavigate.mockReset()
  mockReschedule.mockReset()
  mockReschedule.mockResolvedValue(undefined)
  mockUseIsMobile.mockReset()
  mockUseIsMobile.mockReturnValue(false)
})

describe('test_week_view_7_days', () => {
  it('render → 7 columns', () => {
    renderPage()
    const columns = screen.getAllByTestId('day-column')
    expect(columns).toHaveLength(7)
  })
})

describe('test_month_view_correct_days', () => {
  it('March 2026 → 31 day cells not outside month', async () => {
    const user = userEvent.setup()
    renderPage({ initialDate: new Date('2026-03-01') })
    const monthBtn = screen.getByRole('button', { name: /month/i })
    await user.click(monthBtn)
    const dayCells = screen.getAllByTestId('month-day-cell')
    const marchCells = dayCells.filter(c => !c.dataset.outside)
    expect(marchCells.length).toBe(31)
  })
})

describe('test_month_view_header_sun_sat', () => {
  it('month view → first header is Sun, last is Sat', async () => {
    const user = userEvent.setup()
    renderPage({ initialDate: new Date(2026, 2, 1) }) // local midnight, avoids UTC shift
    const monthBtn = screen.getByRole('button', { name: /month/i })
    await user.click(monthBtn)
    const headers = screen.getAllByText(/^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)$/)
    expect(headers[0]).toHaveTextContent('Sun')
    expect(headers[6]).toHaveTextContent('Sat')
  })
})

describe('test_workouts_on_dates', () => {
  it('3 workouts → 3 cards', () => {
    renderPage({ initialDate: new Date('2026-03-09') })
    const cards = screen.getAllByTestId('workout-card')
    expect(cards).toHaveLength(3)
  })
})

describe('test_card_name_duration', () => {
  it('card → name and clock duration', async () => {
    renderPage({ initialDate: new Date('2026-03-09') })
    const nameEl = await screen.findByText('Easy Run')
    const card = nameEl.closest('[data-testid="workout-card"]') as HTMLElement
    // 2700s = 45:00 in clock format
    expect(within(card).getByText('45:00')).toBeInTheDocument()
  })
})

describe('test_card_sync_status', () => {
  it('synced workout → green sync icon', () => {
    renderPage({ initialDate: new Date('2026-03-09') })
    const syncedIcon = screen.getAllByTestId('workout-card')
      .flatMap(c => Array.from(c.querySelectorAll('[data-sync="synced"]')))
    expect(syncedIcon.length).toBeGreaterThan(0)
    expect(syncedIcon[0]).toHaveClass('text-green-500')
  })
})

describe('test_click_day_opens_picker', () => {
  it('click empty day → picker modal opens', async () => {
    const user = userEvent.setup()
    renderPage()
    const addBtn = screen.getAllByRole('button', { name: /add workout/i })[0]
    await user.click(addBtn)
    expect(screen.getByRole('dialog', { name: /pick a workout/i })).toBeInTheDocument()
  })
})

describe('test_toggle_week_month', () => {
  it('toggle → view switches', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(screen.getAllByTestId('day-column')).toHaveLength(7)
    await user.click(screen.getByRole('button', { name: /month/i }))
    expect(screen.queryAllByTestId('day-column')).toHaveLength(0)
    expect(screen.getByTestId('month-grid')).toBeInTheDocument()
  })
})

describe('test_navigate_prev_next', () => {
  it('next arrow → dates shift forward', async () => {
    const user = userEvent.setup()
    renderPage()
    const headers = screen.getAllByTestId('day-header')
    const firstDateBefore = headers[0].textContent
    await user.click(screen.getByRole('button', { name: /next/i }))
    const headersAfter = screen.getAllByTestId('day-header')
    expect(headersAfter[0].textContent).not.toBe(firstDateBefore)
  })
})

describe('test_sync_all_button', () => {
  // Fake timers scoped to this describe block; always restored in afterEach.
  // Use fireEvent (not userEvent) for clicks — userEvent uses internal timers
  // that hang when vi.useFakeTimers() is active.
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('click sync all → spinner shown immediately, syncAllWorkouts called after 2000ms', async () => {
    mockSyncAll.mockResolvedValue(undefined)
    renderPage()
    // Synchronous click — no userEvent timer issues
    fireEvent.click(screen.getByRole('button', { name: /sync all/i }))
    // Spinner state: label switches and button is disabled
    expect(screen.getByRole('button', { name: /syncing/i })).toBeDisabled()
    // API must not be called yet — debounce is still pending
    expect(mockSyncAll).not.toHaveBeenCalled()
    // Advance past the 2000ms debounce window; wrap in act so React flushes state updates
    await act(() => vi.advanceTimersByTimeAsync(2000))
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
    renderPage({ initialDate: new Date('2026-03-09') })
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
    renderPage({ initialDate: new Date('2026-03-09') })
    await screen.findByText('Easy Run')
    const cards = screen.getAllByTestId('workout-card')
    cards.forEach(card => {
      expect(card.textContent).not.toMatch(/\d+:\d{2}/)
    })
  })
})

describe('test_garmin_toolbar_button', () => {
  it('shows Garmin toolbar button when connected', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    renderPage({ initialDate: new Date('2026-03-09') })
    expect(await screen.findByRole('button', { name: /Garmin Connected/i })).toBeInTheDocument()
  })

  it('shows Garmin toolbar button when not connected', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: false })
    renderPage({ initialDate: new Date('2026-03-09') })
    expect(await screen.findByRole('button', { name: /Garmin Not Connected/i })).toBeInTheDocument()
  })

  it('does not show Garmin toolbar button while loading', async () => {
    mockGetGarminStatus.mockReturnValue(new Promise(() => {}))
    renderPage({ initialDate: new Date('2026-03-09') })
    await act(async () => {})
    expect(screen.queryByRole('button', { name: /Garmin/i })).not.toBeInTheDocument()
  })

  it('clicking Garmin toolbar button navigates to /settings', async () => {
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    const user = userEvent.setup()
    renderPage({ initialDate: new Date('2026-03-09') })
    const btn = await screen.findByRole('button', { name: /Garmin Connected/i })
    await user.click(btn)
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
  })
})

describe('test_mobile_reschedule_navigates_to_new_date', () => {
  it('mobile: after reschedule, day strip selects the new date', async () => {
    // Arrange — mobile view, week March 8–14 (Sun-Sat), selectedDay starts on March 9 (Mon)
    mockUseIsMobile.mockReturnValue(true)
    mockReschedule.mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderPage({ initialDate: new Date(2026, 2, 9) }) // local midnight

    // The mobile strip shows days for the week; workout 1 is on 2026-03-09
    const card = await screen.findByTestId('mobile-workout-card-1')
    await user.click(card)

    // Panel opens — find the date input inside the detail panel
    const dateInput = await screen.findByDisplayValue('2026-03-09')
    fireEvent.change(dateInput, { target: { value: '2026-03-12' } })

    // Wait for async reschedule + state update
    await screen.findByRole('button', { name: 'Select 2026-03-12', pressed: true })
  })
})

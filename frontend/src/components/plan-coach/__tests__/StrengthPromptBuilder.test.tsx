/// <reference types="vitest" />
import { describe, it, expect } from 'vitest'
import { buildStrengthPrompt } from '../StrengthPromptBuilder'
import type { GarminActivity } from '../../../api/types'

const noActivity: GarminActivity[] = []

describe('buildStrengthPrompt', () => {
  it('includes training days in prompt', () => {
    const p = buildStrengthPrompt({
      days: ['Monday', 'Wednesday', 'Friday'],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Monday, Wednesday, Friday')
    expect(p).toContain('3 days/week')
  })

  it('includes equipment list when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: ['Barbell', 'Dumbbells'],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Barbell, Dumbbells')
  })

  it('includes focus when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: 'Running-specific (glute/hip/core)',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Running-specific (glute/hip/core)')
  })

  it('includes health notes when non-empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: 'returning from knee injury',
      activities: noActivity,
    })
    expect(p).toContain('returning from knee injury')
  })

  it('omits health notes section when empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '   ',
      activities: noActivity,
    })
    expect(p).not.toContain('health')
    expect(p).not.toContain('shape')
  })

  it('includes recent strength activities in prompt', () => {
    const acts: GarminActivity[] = [{
      id: 1,
      garmin_activity_id: 'g1',
      activity_type: 'strength_training',
      name: 'Strength Training',
      start_time: '2026-06-01T08:00:00',
      date: '2026-06-01',
      duration_sec: 2700,
      distance_m: 0,
      avg_hr: 120,
      max_hr: null,
      avg_pace_sec_per_km: null,
      calories: null,
    }]
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: acts,
    })
    expect(p).toContain('2026-06-01')
    expect(p).toContain('45min')
    expect(p).toContain('Recent Training')
  })

  it('omits activity section when no activities', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).not.toContain('Recent Training')
  })

  it('always includes the strength shorthand grammar', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Squat 3x5@80kg')
    expect(p).toContain('RPE')
    expect(p).toContain('exercise catalog')
    expect(p).toContain('strength_plan.csv')
  })

  it('uses placeholders when no days or equipment selected', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('[your training days]')
    expect(p).toContain('[any equipment]')
  })
})

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import { StrengthPromptBuilder } from '../StrengthPromptBuilder'

const { mockFetchCalendarRange } = vi.hoisted(() => ({
  mockFetchCalendarRange: vi.fn(),
}))

vi.mock('../../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/client')>()
  return { ...actual, fetchCalendarRange: mockFetchCalendarRange }
})

describe('StrengthPromptBuilder component', () => {
  beforeEach(() => {
    mockFetchCalendarRange.mockReset()
  })

  it('renders all form sections', () => {
    render(<StrengthPromptBuilder />)
    expect(screen.getByRole('button', { name: 'Mon' })).toBeInTheDocument() // training days section
    expect(screen.getByRole('button', { name: /barbell/i })).toBeInTheDocument() // equipment section
    expect(screen.getByLabelText(/training focus/i)).toBeInTheDocument() // focus dropdown
    expect(screen.getByLabelText(/current health/i)).toBeInTheDocument() // health textarea
    expect(screen.getByText(/generated prompt/i)).toBeInTheDocument() // prompt section
  })

  it('shows all 7 day-of-week toggle buttons', () => {
    render(<StrengthPromptBuilder />)
    for (const short of ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) {
      expect(screen.getByRole('button', { name: short })).toBeInTheDocument()
    }
  })

  it('toggles a training day on click', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    const mon = screen.getByRole('button', { name: 'Mon' })
    expect(mon).toHaveAttribute('aria-pressed', 'false')
    await user.click(mon)
    expect(mon).toHaveAttribute('aria-pressed', 'true')
  })

  it('toggles equipment on click', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    const barbell = screen.getByRole('button', { name: /barbell/i })
    expect(barbell).toHaveAttribute('aria-pressed', 'false')
    await user.click(barbell)
    expect(barbell).toHaveAttribute('aria-pressed', 'true')
  })

  it('updates prompt live when a day is selected', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    expect(screen.getByRole('code')).toHaveTextContent('[your training days]')
    await user.click(screen.getByRole('button', { name: 'Mon' }))
    expect(screen.getByRole('code')).toHaveTextContent('Monday')
  })

  it('shows copy button and changes label on copy', async () => {
    const user = userEvent.setup()
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      configurable: true,
    })
    render(<StrengthPromptBuilder />)
    const copy = screen.getByRole('button', { name: /copy prompt/i })
    expect(copy).toBeInTheDocument()
    expect(copy).toHaveTextContent('Copy')
    await user.click(copy)
    await screen.findByText('✓ Copied')
  })

  it('fetch button is shown with correct initial label', () => {
    render(<StrengthPromptBuilder />)
    expect(
      screen.getByRole('button', { name: /fetch.*strength/i })
    ).toBeInTheDocument()
  })

  it('shows activity count after successful fetch', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockResolvedValue({
      workouts: [
        {
          scheduled_date: '2026-06-01',
          activity: {
            id: 1,
            garmin_activity_id: 'g1',
            activity_type: 'strength_training',
            name: 'Strength Training',
            start_time: '2026-06-01T08:00:00',
            date: '2026-06-01',
            duration_sec: 2700,
            distance_m: 0,
            avg_hr: 120,
            max_hr: null,
            avg_pace_sec_per_km: null,
            calories: null,
          },
        },
        {
          scheduled_date: '2026-06-02',
          activity: {
            id: 2,
            garmin_activity_id: 'g2',
            activity_type: 'running',
            name: 'Easy Run',
            start_time: '2026-06-02T07:00:00',
            date: '2026-06-02',
            duration_sec: 3600,
            distance_m: 8000,
            avg_hr: 130,
            max_hr: null,
            avg_pace_sec_per_km: 450,
            calories: null,
          },
        },
      ],
      unplanned_activities: [],
      week_start: '2026-05-19',
    })

    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))

    await screen.findByText(/1 activity included/i)
    expect(screen.getByRole('code')).toHaveTextContent('Recent Training')
    expect(screen.getByRole('code')).not.toHaveTextContent('running')
  })

  it('shows empty feedback when no strength activities found', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockResolvedValue({
      workouts: [],
      unplanned_activities: [],
      week_start: '2026-05-19',
    })
    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))
    await screen.findByText(/no recent strength/i)
  })

  it('shows error feedback when fetch fails', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockRejectedValue(new Error('network'))
    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))
    await screen.findByText(/fetch failed/i)
  })
})

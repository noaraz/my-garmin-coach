// frontend/src/tests/WorkoutPicker.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { WorkoutPicker } from '../components/calendar/WorkoutPicker'
import type { WorkoutTemplate } from '../api/types'

const makeTemplate = (id: number, name: string): WorkoutTemplate => ({
  id,
  name,
  description: null,
  sport_type: 'running',
  estimated_duration_sec: null,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
})

const templates = [
  makeTemplate(1, 'Easy Run'),
  makeTemplate(2, 'Tempo Intervals'),
  makeTemplate(3, 'Long Run'),
]

const defaultProps = {
  templates,
  onSchedule: vi.fn(),
  onClose: vi.fn(),
}

describe('WorkoutPicker search', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_renders_all_templates_when_search_is_empty', () => {
    render(<WorkoutPicker {...defaultProps} />)
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
    expect(screen.getByText('Tempo Intervals')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
  })

  it('test_search_filters_templates_by_name_substring', async () => {
    const user = userEvent.setup()
    render(<WorkoutPicker {...defaultProps} />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'run')
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
    expect(screen.queryByText('Tempo Intervals')).not.toBeInTheDocument()
  })

  it('test_search_is_case_insensitive', async () => {
    const user = userEvent.setup()
    render(<WorkoutPicker {...defaultProps} />)
    await user.type(screen.getByRole('textbox'), 'TEMPO')
    expect(screen.getByText('Tempo Intervals')).toBeInTheDocument()
    expect(screen.queryByText('Easy Run')).not.toBeInTheDocument()
  })

  it('test_shows_empty_state_when_no_templates_match', async () => {
    const user = userEvent.setup()
    render(<WorkoutPicker {...defaultProps} />)
    await user.type(screen.getByRole('textbox'), 'zzznomatch')
    expect(screen.getByText('No workouts match your search')).toBeInTheDocument()
    expect(screen.queryByText('Easy Run')).not.toBeInTheDocument()
  })

  it('test_clearing_search_restores_full_list', async () => {
    const user = userEvent.setup()
    render(<WorkoutPicker {...defaultProps} />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'tempo')
    expect(screen.queryByText('Easy Run')).not.toBeInTheDocument()
    await user.clear(input)
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
    expect(screen.getByText('Tempo Intervals')).toBeInTheDocument()
    expect(screen.getByText('Long Run')).toBeInTheDocument()
  })
})

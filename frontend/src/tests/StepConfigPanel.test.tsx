import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StepConfigPanel } from '../components/builder/StepConfigPanel'
import type { WorkoutStep } from '../api/types'

const baseStep: WorkoutStep = {
  id: 'test-1',
  type: 'interval',
  duration_type: 'time',
  duration_sec: 300,
  target_type: 'hr_zone',
  zone: 4,
}

const mockOnChange = vi.fn()

describe('test_duration_toggle', () => {
  it('toggle time↔distance → duration_type changes', async () => {
    const user = userEvent.setup()
    render(<StepConfigPanel step={baseStep} onChange={mockOnChange} />)
    const toggle = screen.getByRole('button', { name: /distance/i })
    await user.click(toggle)
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ duration_type: 'distance' })
    )
  })
})

describe('test_time_input_mm_ss', () => {
  it('"5:00" → 300s stored', async () => {
    const user = userEvent.setup()
    render(<StepConfigPanel step={baseStep} onChange={mockOnChange} />)
    const input = screen.getByLabelText(/duration/i)
    await user.clear(input)
    await user.type(input, '5:00')
    await user.tab()
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ duration_sec: 300 })
    )
  })
})

describe('test_distance_input_km', () => {
  it('"1.5" km → 1500m stored', async () => {
    const user = userEvent.setup()
    const distanceStep = { ...baseStep, duration_type: 'distance' as const, distance_m: 1000 }
    render(<StepConfigPanel step={distanceStep} onChange={mockOnChange} />)
    const input = screen.getByLabelText(/distance/i)
    await user.clear(input)
    await user.type(input, '1.5')
    await user.tab()
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ distance_m: 1500 })
    )
  })
})

describe('test_target_type_dropdown', () => {
  it('dropdown has HR zone, Pace zone, Open', () => {
    render(<StepConfigPanel step={baseStep} onChange={mockOnChange} />)
    const dropdown = screen.getByRole('combobox', { name: /target/i })
    expect(dropdown).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /hr zone/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /pace zone/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /open/i })).toBeInTheDocument()
  })
})

describe('test_zone_selector_hr', () => {
  it('zone dropdown has zones 1-5', () => {
    render(<StepConfigPanel step={baseStep} onChange={mockOnChange} />)
    const zoneSelect = screen.getByRole('combobox', { name: /zone/i })
    expect(zoneSelect).toBeInTheDocument()
    for (let z = 1; z <= 5; z++) {
      expect(screen.getByRole('option', { name: new RegExp(`zone ${z}|z${z}`, 'i') })).toBeInTheDocument()
    }
  })
})

describe('test_repeat_count_input', () => {
  it('repeat group panel shows count input', async () => {
    const user = userEvent.setup()
    const repeatGroup = { id: 'r1', type: 'repeat' as const, repeat_count: 3, steps: [] }
    render(<StepConfigPanel step={repeatGroup} onChange={mockOnChange} />)
    const input = screen.getByRole('spinbutton', { name: /repeat/i })
    await user.clear(input)
    await user.type(input, '4')
    await user.tab()
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ repeat_count: 4 })
    )
  })
})

describe('test_notes_field', () => {
  it('type notes → saved', async () => {
    const user = userEvent.setup()
    render(<StepConfigPanel step={baseStep} onChange={mockOnChange} />)
    const notes = screen.getByRole('textbox', { name: /notes/i })
    await user.type(notes, 'Push hard')
    await user.tab()
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ notes: 'Push hard' })
    )
  })
})

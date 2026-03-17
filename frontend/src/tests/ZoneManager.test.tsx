import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ZoneManager } from '../components/zones/ZoneManager'

const mockSaveHRZones = vi.fn()
const mockRecalcHR = vi.fn()
const mockSave = vi.fn()

vi.mock('../hooks/useZones', () => ({
  useZones: () => ({
    hrZones: [
      { id: 1, zone_number: 1, name: 'Z1 Recovery',  lower_bpm: 0,   upper_bpm: 114, calculation_method: 'coggan', pct_lower: 0,    pct_upper: 0.68 },
      { id: 2, zone_number: 2, name: 'Z2 Aerobic',   lower_bpm: 114, upper_bpm: 141, calculation_method: 'coggan', pct_lower: 0.68, pct_upper: 0.83 },
      { id: 3, zone_number: 3, name: 'Z3 Tempo',     lower_bpm: 141, upper_bpm: 157, calculation_method: 'coggan', pct_lower: 0.83, pct_upper: 0.94 },
      { id: 4, zone_number: 4, name: 'Z4 Threshold', lower_bpm: 157, upper_bpm: 170, calculation_method: 'coggan', pct_lower: 0.94, pct_upper: 1.05 },
      { id: 5, zone_number: 5, name: 'Z5 VO2max',    lower_bpm: 170, upper_bpm: 220, calculation_method: 'coggan', pct_lower: 1.05, pct_upper: 1.2  },
    ],
    paceZones: [
      { id: 1, zone_number: 1, name: 'Z1', lower_pace: 360, upper_pace: 330, calculation_method: 'pct_threshold', pct_lower: 1.29, pct_upper: 1.14 },
      { id: 2, zone_number: 2, name: 'Z2', lower_pace: 330, upper_pace: 300, calculation_method: 'pct_threshold', pct_lower: 1.14, pct_upper: 1.06 },
      { id: 3, zone_number: 3, name: 'Z3', lower_pace: 300, upper_pace: 285, calculation_method: 'pct_threshold', pct_lower: 1.06, pct_upper: 1.01 },
      { id: 4, zone_number: 4, name: 'Z4', lower_pace: 285, upper_pace: 270, calculation_method: 'pct_threshold', pct_lower: 1.01, pct_upper: 0.97 },
      { id: 5, zone_number: 5, name: 'Z5', lower_pace: 270, upper_pace: 240, calculation_method: 'pct_threshold', pct_lower: 0.97, pct_upper: 0.9  },
    ],
    loading: false,
    error: null,
    saveHRZones: mockSaveHRZones,
    recalcHR: mockRecalcHR,
    recalcPace: vi.fn(),
  }),
}))

vi.mock('../hooks/useProfile', () => ({
  useProfile: () => ({
    profile: { id: 1, name: 'Athlete', lthr: 162, threshold_pace: 270, max_hr: 185, resting_hr: 50 },
    loading: false,
    error: null,
    save: mockSave,
  }),
}))

beforeEach(() => {
  mockSaveHRZones.mockReset()
  mockRecalcHR.mockReset()
  mockSave.mockReset()
})

describe('test_renders_5_hr_zone_rows', () => {
  it('zones loaded → 5 rows', () => {
    render(<ZoneManager />)
    expect(screen.getByText('Z1 Recovery')).toBeInTheDocument()
    expect(screen.getByText('Z5 VO2max')).toBeInTheDocument()
    const table = screen.getByTestId('hr-zone-table')
    const rows = table.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(5)
  })
})

describe('test_renders_5_pace_zone_rows', () => {
  it('zones loaded → 5 pace rows', () => {
    render(<ZoneManager />)
    const section = screen.getByTestId('pace-zone-table')
    const rows = section.querySelectorAll('tbody tr')
    expect(rows).toHaveLength(5)
  })
})

describe('test_lthr_input_shows_current', () => {
  it('profile loaded → LTHR shown', () => {
    render(<ZoneManager />)
    const input = screen.getByLabelText(/lthr/i)
    expect(input).toHaveValue(162)
  })
})

describe('test_change_lthr_and_save', () => {
  it('type new LTHR, save → save called with lthr 165', async () => {
    const user = userEvent.setup()
    mockSave.mockResolvedValue(undefined)
    render(<ZoneManager />)
    const input = screen.getByLabelText(/lthr/i)
    await user.clear(input)
    await user.type(input, '165')
    const saveBtn = screen.getByRole('button', { name: /save/i })
    await user.click(saveBtn)
    expect(mockSave).toHaveBeenCalledWith(expect.objectContaining({ lthr: 165 }))
  })
})

describe('test_recalculate_button', () => {
  it('click recalculate → recalcHR called', async () => {
    const user = userEvent.setup()
    mockRecalcHR.mockResolvedValue(undefined)
    render(<ZoneManager />)
    const btn = screen.getByRole('button', { name: /recalculate/i })
    await user.click(btn)
    expect(mockRecalcHR).toHaveBeenCalledTimes(1)
  })
})

describe('test_zone_boundaries_editable', () => {
  it('click zone BPM cell → inline input appears', async () => {
    const user = userEvent.setup()
    render(<ZoneManager />)
    const cell = screen.getByTestId('hr-upper-bpm-2')
    await user.click(cell)
    expect(screen.getByRole('spinbutton', { name: /upper bpm/i })).toBeInTheDocument()
  })
})

describe('test_success_feedback', () => {
  it('save succeeds → success toast shown', async () => {
    const user = userEvent.setup()
    mockSave.mockResolvedValue(undefined)
    render(<ZoneManager />)
    const saveBtn = screen.getByRole('button', { name: /save/i })
    await user.click(saveBtn)
    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(/saved/i)
    })
  })
})

describe('test_error_on_failure', () => {
  it('save fails → error message shown', async () => {
    const user = userEvent.setup()
    mockSave.mockRejectedValue(new Error('422: No LTHR set'))
    render(<ZoneManager />)
    const saveBtn = screen.getByRole('button', { name: /save/i })
    await user.click(saveBtn)
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/422: No LTHR set/i)
    })
  })
})

/// <reference types="vitest" />
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { StrengthImportTab } from '../StrengthImportTab'
import type { StrengthValidateResult } from '../../../api/types'

const { mockValidateStrengthCsv, mockCommitPlan, mockNavigate, mockFetchCalendarRange } = vi.hoisted(() => ({
  mockValidateStrengthCsv: vi.fn(),
  mockCommitPlan: vi.fn(),
  mockNavigate: vi.fn(),
  mockFetchCalendarRange: vi.fn(),
}))

vi.mock('../../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/client')>()
  return {
    ...actual,
    validateStrengthCsv: mockValidateStrengthCsv,
    commitPlan: mockCommitPlan,
    fetchCalendarRange: mockFetchCalendarRange,
  }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const validResult: StrengthValidateResult = {
  plan_id: 10,
  sport: 'strength',
  rows: [
    {
      date: '2026-06-01',
      name: 'Lower body',
      status: 'valid',
      steps: [
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
      ],
      errors: [],
    },
  ],
}

const errorResult: StrengthValidateResult = {
  plan_id: -1,
  sport: 'strength',
  rows: [
    {
      date: '2026-06-01',
      name: 'Bad workout',
      status: 'error',
      steps: [],
      errors: [{ code: 'unknown_exercise', message: '"Nordic Curl" not in catalog' }],
    },
  ],
}

function renderTab() {
  return render(
    <MemoryRouter>
      <StrengthImportTab />
    </MemoryRouter>
  )
}

describe('StrengthImportTab', () => {
  beforeEach(() => {
    mockValidateStrengthCsv.mockReset()
    mockCommitPlan.mockReset()
    mockNavigate.mockReset()
    mockFetchCalendarRange.mockResolvedValue({
      workouts: [],
      unplanned_activities: [],
      week_start: '2026-05-19',
    })
  })

  it('renders prompt builder and file upload', () => {
    renderTab()
    // Prompt builder should be present (contains generated prompt)
    expect(screen.getByText(/generated prompt/i)).toBeInTheDocument()
    // File input present
    expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
  })

  it('Validate button disabled before file selected', () => {
    renderTab()
    expect(screen.getByRole('button', { name: /validate/i })).toBeDisabled()
  })

  it('validates file and shows exercise pills', async () => {
    const user = userEvent.setup()
    mockValidateStrengthCsv.mockResolvedValue(validResult)
    renderTab()

    const csv = 'date,name,steps\n2026-06-01,Lower body,Squat 3x5@80kg\n'
    const file = new File([csv], 'strength.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(mockValidateStrengthCsv).toHaveBeenCalledTimes(1)
      expect(screen.getByText(/back squat/i)).toBeInTheDocument()
    })
  })

  it('Import Plan button enabled when all rows valid', async () => {
    const user = userEvent.setup()
    mockValidateStrengthCsv.mockResolvedValue(validResult)
    renderTab()

    const csv = 'date,name,steps\n2026-06-01,Lower body,Squat 3x5@80kg\n'
    const file = new File([csv], 'strength.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import plan/i })).not.toBeDisabled()
    })
  })

  it('Import Plan button disabled when errors present', async () => {
    const user = userEvent.setup()
    mockValidateStrengthCsv.mockResolvedValue(errorResult)
    renderTab()

    const csv = 'date,name,steps\n2026-06-01,Bad,Nordic Curl 3x6@bw\n'
    const file = new File([csv], 'strength.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByText(/Nordic Curl/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /import plan/i })).toBeDisabled()
    })
  })

  it('commits with sport=strength and navigates to /calendar', async () => {
    const user = userEvent.setup()
    mockValidateStrengthCsv.mockResolvedValue(validResult)
    mockCommitPlan.mockResolvedValue({ plan_id: 10, name: 'Strength Plan', workout_count: 1, start_date: '2026-06-01' })
    renderTab()

    const csv = 'date,name,steps\n2026-06-01,Lower body,Squat 3x5@80kg\n'
    const file = new File([csv], 'strength.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import plan/i })).not.toBeDisabled()
    })

    await user.click(screen.getByRole('button', { name: /import plan/i }))

    await waitFor(() => {
      expect(mockCommitPlan).toHaveBeenCalledWith(10, 'strength')
      expect(mockNavigate).toHaveBeenCalledWith('/calendar')
    })
  })
})

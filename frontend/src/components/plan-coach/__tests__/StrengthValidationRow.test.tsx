/// <reference types="vitest" />
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StrengthValidationRow, summarizeStrengthSets } from '../StrengthValidationRow'
import type { StrengthValidateRow } from '../../../api/types'

const backSquatStep = {
  kind: 'strength_exercise' as const,
  exercise_key: 'back_squat',
  garmin_category: 'SQUAT',
  garmin_name: 'BARBELL_BACK_SQUAT',
  sets: [
    { reps: 5, load: { type: 'kg' as const, value: 80 } },
    { reps: 5, load: { type: 'kg' as const, value: 80 } },
    { reps: 5, load: { type: 'kg' as const, value: 80 } },
  ],
  note: null,
}

const rdlStep = {
  kind: 'strength_exercise' as const,
  exercise_key: 'romanian_deadlift',
  garmin_category: 'DEADLIFT',
  garmin_name: 'ROMANIAN_DEADLIFT',
  sets: [
    { reps: 8, load: { type: 'rpe' as const, value: 8 } },
    { reps: 8, load: { type: 'rpe' as const, value: 8 } },
    { reps: 8, load: { type: 'rpe' as const, value: 8 } },
  ],
  note: null,
}

const validRow: StrengthValidateRow = {
  date: '2026-06-01',
  name: 'Lower body',
  status: 'valid',
  steps: [backSquatStep, rdlStep],
  errors: [],
}

describe('StrengthValidationRow', () => {
  it('renders exercise names as pills', () => {
    render(<StrengthValidationRow row={validRow} />)
    expect(screen.getByText(/back squat/i)).toBeInTheDocument()
    expect(screen.getByText(/romanian deadlift/i)).toBeInTheDocument()
  })

  it('renders set summaries in pills', () => {
    render(<StrengthValidationRow row={validRow} />)
    expect(screen.getByText(/3 × 5 @ 80kg/i)).toBeInTheDocument()
    expect(screen.getByText(/3 × 8 @ RPE 8/i)).toBeInTheDocument()
  })

  it('reveals Garmin mapping on disclosure click', () => {
    render(<StrengthValidationRow row={validRow} />)
    fireEvent.click(screen.getByText(/show garmin mapping/i))
    expect(screen.getByText(/BARBELL_BACK_SQUAT/)).toBeInTheDocument()
    expect(screen.getByText(/ROMANIAN_DEADLIFT/)).toBeInTheDocument()
  })

  it('hides mapping after second click', () => {
    render(<StrengthValidationRow row={validRow} />)
    fireEvent.click(screen.getByText(/show garmin mapping/i))
    expect(screen.getByText(/hide garmin mapping/i)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/hide garmin mapping/i))
    expect(screen.getByText(/show garmin mapping/i)).toBeInTheDocument()
    expect(screen.queryByText(/BARBELL_BACK_SQUAT/)).not.toBeInTheDocument()
  })

  it('shows error message for unknown_exercise', () => {
    const errorRow: StrengthValidateRow = {
      date: '2026-06-01',
      name: 'Bad workout',
      status: 'error',
      steps: [],
      errors: [{ code: 'unknown_exercise', message: '"Nordic Curl" not in catalog' }],
    }
    render(<StrengthValidationRow row={errorRow} />)
    expect(screen.getByText(/Nordic Curl/)).toBeInTheDocument()
    expect(screen.getByText(/edit the row or pick a known exercise/i)).toBeInTheDocument()
  })

  it('does not show garmin mapping button for error rows', () => {
    const errorRow: StrengthValidateRow = {
      ...validRow,
      status: 'error',
      errors: [{ code: 'load_required', message: 'load required' }],
    }
    render(<StrengthValidationRow row={errorRow} />)
    expect(screen.queryByText(/show garmin mapping/i)).not.toBeInTheDocument()
  })
})

describe('summarizeStrengthSets', () => {
  it('uniform kg: "3 × 5 @ 80kg"', () => {
    const sets = [
      { reps: 5, load: { type: 'kg' as const, value: 80 } },
      { reps: 5, load: { type: 'kg' as const, value: 80 } },
      { reps: 5, load: { type: 'kg' as const, value: 80 } },
    ]
    expect(summarizeStrengthSets(sets)).toBe('3 × 5 @ 80kg')
  })

  it('uniform rpe: "3 × 8 @ RPE 8"', () => {
    const sets = [
      { reps: 8, load: { type: 'rpe' as const, value: 8 } },
      { reps: 8, load: { type: 'rpe' as const, value: 8 } },
      { reps: 8, load: { type: 'rpe' as const, value: 8 } },
    ]
    expect(summarizeStrengthSets(sets)).toBe('3 × 8 @ RPE 8')
  })

  it('duration sets: "3 × 45s"', () => {
    const sets = [{ duration_sec: 45 }, { duration_sec: 45 }, { duration_sec: 45 }]
    expect(summarizeStrengthSets(sets)).toBe('3 × 45s')
  })

  it('bodyweight: "3 × 10 @ bw"', () => {
    const sets = [
      { reps: 10, load: { type: 'bodyweight' as const } },
      { reps: 10, load: { type: 'bodyweight' as const } },
      { reps: 10, load: { type: 'bodyweight' as const } },
    ]
    expect(summarizeStrengthSets(sets)).toBe('3 × 10 @ bw')
  })

  it('kg variance: "5 @ 60kg · 5 @ 70kg · 5 @ 80kg"', () => {
    const sets = [
      { reps: 5, load: { type: 'kg' as const, value: 60 } },
      { reps: 5, load: { type: 'kg' as const, value: 70 } },
      { reps: 5, load: { type: 'kg' as const, value: 80 } },
    ]
    expect(summarizeStrengthSets(sets)).toBe('5 @ 60kg · 5 @ 70kg · 5 @ 80kg')
  })
})

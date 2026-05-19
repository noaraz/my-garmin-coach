import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StrengthExerciseRow } from '../StrengthExerciseRow'
import type { StrengthExerciseStep } from '../../../api/types'

function makeStep(overrides: Partial<StrengthExerciseStep> = {}): StrengthExerciseStep {
  return {
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
    ...overrides,
  }
}

describe('StrengthExerciseRow', () => {
  it('renders compact "3 × 5 @ 80kg" when all sets identical', () => {
    render(<StrengthExerciseRow step={makeStep()} />)
    expect(screen.getByText(/Back Squat/i)).toBeInTheDocument()
    expect(screen.getByText(/3 × 5 @ 80kg/)).toBeInTheDocument()
  })

  it('renders per-set chips "5 @ 60kg · 70kg · 80kg" when kg varies', () => {
    const step = makeStep({
      sets: [
        { reps: 5, load: { type: 'kg', value: 60 } },
        { reps: 5, load: { type: 'kg', value: 70 } },
        { reps: 5, load: { type: 'kg', value: 80 } },
      ],
    })
    render(<StrengthExerciseRow step={step} />)
    expect(screen.getByText(/5 @ 60kg · 70kg · 80kg/)).toBeInTheDocument()
  })

  it('renders chip list with mixed load types', () => {
    const step = makeStep({
      sets: [
        { reps: 5, load: { type: 'kg', value: 60 } },
        { reps: 5, load: { type: 'rpe', value: 7 } },
        { reps: 5, load: { type: 'rpe', value: 8 } },
      ],
    })
    render(<StrengthExerciseRow step={step} />)
    expect(screen.getByText(/5 @ 60kg · RPE7 · RPE8/)).toBeInTheDocument()
  })

  it('renders duration as "3 × 45s"', () => {
    const step = makeStep({
      exercise_key: 'front_plank',
      garmin_category: 'PLANK',
      garmin_name: 'FRONT_PLANK',
      sets: [{ duration_sec: 45 }, { duration_sec: 45 }, { duration_sec: 45 }],
    })
    render(<StrengthExerciseRow step={step} />)
    expect(screen.getByText(/Front Plank/i)).toBeInTheDocument()
    expect(screen.getByText(/3 × 45s/)).toBeInTheDocument()
  })

  it('renders bodyweight sets as "3 × 10 @ bw"', () => {
    const step = makeStep({
      exercise_key: 'walking_lunge',
      garmin_category: 'LUNGE',
      garmin_name: 'WALKING_LUNGE',
      sets: [
        { reps: 10, load: { type: 'bodyweight' } },
        { reps: 10, load: { type: 'bodyweight' } },
        { reps: 10, load: { type: 'bodyweight' } },
      ],
    })
    render(<StrengthExerciseRow step={step} />)
    expect(screen.getByText(/3 × 10 @ bw/)).toBeInTheDocument()
  })
})

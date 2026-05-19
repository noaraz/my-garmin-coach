import type { StrengthExerciseStep } from '../../api/types'
import { summarizeStrengthSets, prettyExerciseName } from '../../utils/workoutStats'

export function StrengthExerciseRow({ step }: { step: StrengthExerciseStep }) {
  const summary = summarizeStrengthSets(step.sets as Parameters<typeof summarizeStrengthSets>[0])

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        gap: '8px',
        padding: '4px 0',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span
        style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-primary)',
          fontWeight: 500,
        }}
      >
        {prettyExerciseName(step.exercise_key)}
      </span>
      <span
        style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '12px',
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap',
        }}
      >
        {summary}
      </span>
    </div>
  )
}

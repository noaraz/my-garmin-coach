import { useState } from 'react'
import type { StrengthValidateRow, StrengthExerciseStep, StrengthSet } from '../../api/types'

// Pure helper: summarize sets as a compact string
// Examples: "3 × 5 @ 80kg", "3 × 8 @ RPE 8", "3 × 45s", "3 × 10 @ bw"
// Per-set variance: "5 @ 60kg · 5 @ 70kg · 5 @ 80kg"
export function summarizeStrengthSets(sets: StrengthSet[]): string {
  if (sets.length === 0) return ''

  const describeSingleSet = (s: StrengthSet): string => {
    if (s.duration_sec !== undefined) return `${s.duration_sec}s`
    const reps = s.reps ?? '?'
    if (!s.load) return `${reps}`
    if (s.load.type === 'kg') return `${reps} @ ${s.load.value}kg`
    if (s.load.type === 'rpe') return `${reps} @ RPE ${s.load.value}`
    return `${reps} @ bw`
  }

  // Check if all sets are identical (same reps/duration and load)
  const firstJson = JSON.stringify(sets[0])
  const allSame = sets.every(s => JSON.stringify(s) === firstJson)

  if (allSame) {
    const setDesc = sets[0].duration_sec !== undefined
      ? `${sets.length} × ${sets[0].duration_sec}s`
      : (() => {
          const reps = sets[0].reps ?? '?'
          const load = sets[0].load
          if (!load) return `${sets.length} × ${reps}`
          if (load.type === 'kg') return `${sets.length} × ${reps} @ ${load.value}kg`
          if (load.type === 'rpe') return `${sets.length} × ${reps} @ RPE ${load.value}`
          return `${sets.length} × ${reps} @ bw`
        })()
    return setDesc
  }

  // Per-set variance: show each set
  return sets.map(describeSingleSet).join(' · ')
}

// Pretty-print exercise_key → human readable
function prettyName(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function ExercisePill({ step }: { step: StrengthExerciseStep }) {
  const summary = summarizeStrengthSets(step.sets)
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '3px 10px',
      borderRadius: '4px',
      background: 'var(--bg-surface-2)',
      border: '1px solid var(--border)',
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      fontSize: '12px',
      color: 'var(--text-primary)',
      marginRight: '6px',
      marginBottom: '4px',
    }}>
      <span>{prettyName(step.exercise_key)}</span>
      <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{summary}</span>
    </span>
  )
}

export function StrengthValidationRow({ row }: { row: StrengthValidateRow }) {
  const [showMapping, setShowMapping] = useState(false)
  const isError = row.status === 'error'

  return (
    <div style={{
      padding: '10px 12px',
      borderBottom: '1px solid var(--border)',
      background: isError ? 'var(--color-error-bg, var(--bg-surface))' : 'var(--bg-surface)',
    }}>
      {/* Row header: date + name */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginBottom: '6px' }}>
        <span style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '11px',
          color: 'var(--text-muted)',
        }}>
          {row.date}
        </span>
        <span style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 600,
          fontSize: '13px',
          color: 'var(--text-primary)',
        }}>
          {row.name}
        </span>
      </div>

      {/* Error state */}
      {isError && (
        <div>
          {row.errors.map((e, i) => (
            <p key={i} style={{
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '12px',
              color: 'var(--color-error, #e53e3e)',
              margin: '0 0 4px 0',
            }}>
              {e.message} — edit the row or pick a known exercise
            </p>
          ))}
        </div>
      )}

      {/* Valid state: exercise pills */}
      {!isError && row.steps.length > 0 && (
        <div style={{ marginBottom: '6px' }}>
          {row.steps.map((step, i) => (
            <ExercisePill key={i} step={step} />
          ))}
        </div>
      )}

      {/* Garmin mapping disclosure */}
      {!isError && row.steps.length > 0 && (
        <button
          onClick={() => setShowMapping(v => !v)}
          style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '11px',
            color: 'var(--text-muted)',
            background: 'none',
            border: 'none',
            padding: '0',
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          {showMapping ? 'Hide Garmin mapping' : 'Show Garmin mapping'}
        </button>
      )}

      {showMapping && (
        <div style={{ marginTop: '8px' }}>
          {row.steps.map((step, i) => (
            <div key={i} style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-secondary)',
              marginBottom: '2px',
            }}>
              {prettyName(step.exercise_key)} → {step.garmin_category} / {step.garmin_name}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

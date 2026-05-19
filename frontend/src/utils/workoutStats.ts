/** Shared utilities for computing workout duration/distance from steps JSON */

type RawStep = {
  type: string
  duration_sec?: number
  distance_m?: number
  repeat_count?: number
  steps?: RawStep[]
}

function parseSteps(stepsJson: string | null | undefined): RawStep[] | null {
  if (!stepsJson) return null
  try {
    return JSON.parse(stepsJson) as RawStep[]
  } catch {
    return null
  }
}

function sumSteps(arr: RawStep[], field: 'duration_sec' | 'distance_m'): number {
  return arr.reduce((acc, step) => {
    if (step.type === 'repeat') {
      return acc + (step.repeat_count ?? 1) * sumSteps(step.steps ?? [], field)
    }
    return acc + (step[field] ?? 0)
  }, 0)
}

/** Total duration in seconds, falling back to summing step.duration_sec */
export function computeDurationFromSteps(stepsJson: string | null | undefined): number | null {
  const steps = parseSteps(stepsJson)
  if (!steps) return null
  const total = sumSteps(steps, 'duration_sec')
  return total > 0 ? total : null
}

/** Total distance in metres, falling back to summing step.distance_m */
export function computeDistanceFromSteps(stepsJson: string | null | undefined): number | null {
  const steps = parseSteps(stepsJson)
  if (!steps) return null
  const total = sumSteps(steps, 'distance_m')
  return total > 0 ? total : null
}

/** Format seconds as clock-style duration: "28:00", "1:10:00" */
export function formatClock(seconds: number): string {
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

/** Format metres as "12.5 km" */
export function formatKm(metres: number): string {
  return `${(metres / 1000).toFixed(1)} km`
}

// ---------------------------------------------------------------------------
// Strength workout helpers
// ---------------------------------------------------------------------------

type StrengthLoad =
  | { type: 'kg'; value: number }
  | { type: 'rpe'; value: number }
  | { type: 'bodyweight' }

type StrengthSetSpec =
  | { reps: number; load: StrengthLoad }
  | { duration_sec: number }

function formatLoad(load: StrengthLoad): string {
  if (load.type === 'kg') return `${load.value}kg`
  if (load.type === 'rpe') return `RPE${load.value}`
  return 'bw'
}

function setsAreUniform(sets: StrengthSetSpec[]): boolean {
  if (sets.length === 0) return true
  const first = JSON.stringify(sets[0])
  return sets.every(s => JSON.stringify(s) === first)
}

/**
 * Summarize a list of strength sets into a compact display string.
 * Uniform sets:   "3 × 5 @ 80kg"  or  "3 × 45s"
 * Varied sets:    "5 @ 60kg · 70kg · 80kg"
 * Mixed types:    "60kg · RPE7 · RPE8"
 */
export function summarizeStrengthSets(sets: StrengthSetSpec[]): string {
  if (!sets || sets.length === 0) return ''

  const isDuration = sets.every(s => 'duration_sec' in s)
  const isReps = sets.every(s => 'reps' in s)

  if (isDuration) {
    const sec = (sets[0] as { duration_sec: number }).duration_sec
    if (setsAreUniform(sets)) {
      return `${sets.length} × ${sec}s`
    }
    return sets.map(s => `${(s as { duration_sec: number }).duration_sec}s`).join(' · ')
  }

  if (isReps) {
    const repSets = sets as Array<{ reps: number; load: StrengthLoad }>
    if (setsAreUniform(sets)) {
      return `${sets.length} × ${repSets[0].reps} @ ${formatLoad(repSets[0].load)}`
    }
    const reps = repSets[0].reps
    const allSameReps = repSets.every(s => s.reps === reps)
    const loadStr = repSets.map(s => formatLoad(s.load)).join(' · ')
    if (allSameReps) {
      return `${reps} @ ${loadStr}`
    }
    return repSets.map(s => `${s.reps} @ ${formatLoad(s.load)}`).join(' · ')
  }

  return `${sets.length} sets`
}

/** Pretty-print an exercise_key into a human-readable label. */
export function prettyExerciseName(exerciseKey: string): string {
  return exerciseKey
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

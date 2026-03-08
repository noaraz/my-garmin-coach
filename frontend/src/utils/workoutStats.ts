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
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

/** Format metres as "12.5 km" */
export function formatKm(metres: number): string {
  return `${(metres / 1000).toFixed(1)} km`
}

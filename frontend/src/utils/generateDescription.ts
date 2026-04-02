import type { BuilderStep, RepeatGroup, WorkoutStep, PaceZone } from '../api/types'

function isRepeatGroup(step: BuilderStep): step is RepeatGroup {
  return step.type === 'repeat'
}

// Format duration for description one-liner
function fmtDur(step: WorkoutStep & { duration_distance_m?: number }): string {
  if (step.duration_type === 'distance') {
    // Accept both builder key (distance_m) and legacy CSV parser key (duration_distance_m)
    const distM = step.distance_m ?? step.duration_distance_m
    if (distM != null) {
      const km = distM / 1000
      return km === Math.floor(km) ? `${km}K` : `${km.toFixed(1)}K`
    }
  }
  if (step.duration_sec != null) {
    const m = Math.round(step.duration_sec / 60)
    return `${m}m`
  }
  return '?'
}

// Zone label for description
function zoneLabel(step: WorkoutStep): string {
  if (step.target_type === 'open') return ''
  if (step.zone != null) {
    // HR zone gets a suffix; pace zone (or legacy CSV steps without target_type) just @ZN
    return step.target_type === 'hr_zone' ? `@Z${step.zone}(HR)` : `@Z${step.zone}`
  }
  // Default zone by step type (builder steps without explicit zone)
  const defaults: Record<string, string> = {
    warmup: '@Z1', interval: '@Z4', recovery: '@Z1', cooldown: '@Z1'
  }
  return defaults[step.type] ?? ''
}

// Short step description for one-liner
function stepDesc(step: WorkoutStep): string {
  return `${fmtDur(step)}${zoneLabel(step)}`
}

export function generateDescription(steps: BuilderStep[]): string {
  const parts = steps.map(step => {
    if (isRepeatGroup(step)) {
      const inner = step.steps.map(stepDesc).join(' + ')
      return `${step.repeat_count}x (${inner})`
    }
    return stepDesc(step as WorkoutStep)
  })
  return parts.join(', ')
}

// Fallback for templates where description column is null — parses steps JSON
// and generates the description on the fly. Same pattern as computeDurationFromSteps.
export function generateDescriptionFromSteps(stepsJson: string | null | undefined): string | null {
  if (!stepsJson) return null
  try {
    const steps = JSON.parse(stepsJson) as BuilderStep[]
    if (!Array.isArray(steps) || steps.length === 0) return null
    return generateDescription(steps)
  } catch {
    return null
  }
}

// Format pace from sec/km to "mm:ss"
function fmtPace(secPerKm: number): string {
  const mins = Math.floor(secPerKm / 60)
  const secs = Math.round(secPerKm % 60)
  return `${mins}:${String(secs).padStart(2, '0')}`
}

// Default zone for each step type
const DEFAULT_ZONE: Record<string, number> = {
  warmup: 1, recovery: 1, cooldown: 1, interval: 4
}

// Get pace range for a zone from pace zones array
function getPaceRange(zone: number, paceZones: PaceZone[]): string | null {
  const z = paceZones.find(pz => pz.zone_number === zone)
  if (!z) return null
  return `${fmtPace(z.upper_pace)}–${fmtPace(z.lower_pace)} min/km`
}

// Step type display names
const STEP_NAMES: Record<string, string> = {
  warmup: 'Warm up', interval: 'Hard', recovery: 'Easy', cooldown: 'Cooldown'
}

// Format duration for workout details (verbose)
function fmtDurVerbose(step: WorkoutStep): string {
  if (step.duration_type === 'distance' && step.distance_m != null) {
    const km = step.distance_m / 1000
    return `${km.toFixed(2)} km`
  }
  if (step.duration_sec != null) {
    const m = Math.round(step.duration_sec / 60)
    if (m < 60) return `${m} min`
    const h = Math.floor(m / 60)
    const rem = m % 60
    return rem > 0 ? `${h}h ${rem} min` : `${h}h`
  }
  return '?'
}

function stepDetails(step: WorkoutStep, paceZones: PaceZone[], indent = '  '): string {
  const name = STEP_NAMES[step.type] ?? step.type
  const dur = fmtDurVerbose(step)
  let paceStr = ''
  if (step.target_type !== 'open') {
    const effectiveZone = step.zone ?? DEFAULT_ZONE[step.type] ?? 1
    const paceRange = getPaceRange(effectiveZone, paceZones)
    paceStr = paceRange ? ` @ ${paceRange}` : ''
  }
  let line = `${indent}${name}\n${indent}  ${dur}${paceStr}`
  if (step.target_type !== 'open' && step.zone != null) {
    line += `\n${indent}  Zone ${step.zone}`
  }
  return line
}

export function generateWorkoutDetails(steps: BuilderStep[], paceZones: PaceZone[]): string {
  const lines: string[] = []
  for (const step of steps) {
    if (isRepeatGroup(step)) {
      lines.push(`  Repeat ${step.repeat_count} times`)
      step.steps.forEach((inner, i) => {
        lines.push(`    ${i + 1}. ${stepDetails(inner, paceZones, '    ').trim()}`)
      })
    } else {
      lines.push(stepDetails(step as WorkoutStep, paceZones))
    }
  }
  return lines.join('\n')
}

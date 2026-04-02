import { describe, it, expect } from 'vitest'
import { generateDescription, generateWorkoutDetails } from '../utils/generateDescription'
import type { WorkoutStep, PaceZone } from '../api/types'

const PACE_ZONES: PaceZone[] = [
  { id: 1, profile_id: 1, zone_number: 1, name: 'Recovery', lower_pace: 480, upper_pace: 540, calculation_method: 'daniels', pct_lower: 0, pct_upper: 0 },
  { id: 2, profile_id: 1, zone_number: 4, name: 'Threshold', lower_pace: 300, upper_pace: 330, calculation_method: 'daniels', pct_lower: 0, pct_upper: 0 },
]

describe('generateDescription', () => {
  it('omits zone for open target type', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'warmup', target_type: 'open', duration_type: 'time', duration_sec: 600 },
    ]
    expect(generateDescription(steps)).toBe('10m')
  })

  it('omits zone for open target even when zone is explicitly set', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'warmup', target_type: 'open', zone: 1, duration_type: 'time', duration_sec: 600 },
    ]
    expect(generateDescription(steps)).toBe('10m')
  })

  it('includes zone for pace_zone target type', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'warmup', target_type: 'pace_zone', zone: 1, duration_type: 'time', duration_sec: 600 },
    ]
    expect(generateDescription(steps)).toBe('10m@Z1')
  })

  it('includes zone for hr_zone target type', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'interval', target_type: 'hr_zone', zone: 4, duration_type: 'time', duration_sec: 300 },
    ]
    expect(generateDescription(steps)).toBe('5m@Z4(HR)')
  })
})

describe('generateWorkoutDetails', () => {
  it('omits pace range and zone line for open target', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'warmup', target_type: 'open', duration_type: 'time', duration_sec: 600 },
    ]
    const result = generateWorkoutDetails(steps, PACE_ZONES)
    expect(result).not.toContain('min/km')
    expect(result).not.toContain('Zone')
    expect(result).toContain('Warm up')
    expect(result).toContain('10 min')
  })

  it('includes pace range for pace_zone target', () => {
    const steps: WorkoutStep[] = [
      { id: '1', type: 'warmup', target_type: 'pace_zone', zone: 1, duration_type: 'time', duration_sec: 600 },
    ]
    const result = generateWorkoutDetails(steps, PACE_ZONES)
    expect(result).toContain('min/km')
    expect(result).toContain('Zone 1')
  })
})

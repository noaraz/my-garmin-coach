import { describe, it, expect } from 'vitest'
import {
  computeDurationFromSteps,
  computeDistanceFromSteps,
  formatClock,
  formatKm,
} from '../utils/workoutStats'

// ─── computeDurationFromSteps ──────────────────────────────────────────────

describe('test_computeDuration_nullish_input', () => {
  it('null → null', () => {
    expect(computeDurationFromSteps(null)).toBeNull()
  })
  it('undefined → null', () => {
    expect(computeDurationFromSteps(undefined)).toBeNull()
  })
  it('empty string → null', () => {
    expect(computeDurationFromSteps('')).toBeNull()
  })
})

describe('test_computeDuration_invalid_json', () => {
  it('invalid JSON → null (no throw)', () => {
    expect(computeDurationFromSteps('not json')).toBeNull()
  })
  it('partial JSON → null', () => {
    expect(computeDurationFromSteps('[{broken')).toBeNull()
  })
})

describe('test_computeDuration_empty_array', () => {
  it('[] → null (zero total treated as no data)', () => {
    expect(computeDurationFromSteps('[]')).toBeNull()
  })
})

describe('test_computeDuration_simple_steps', () => {
  it('two time steps → sum', () => {
    const steps = JSON.stringify([
      { type: 'warmup',   duration_type: 'time', duration_sec: 600 },
      { type: 'cooldown', duration_type: 'time', duration_sec: 300 },
    ])
    expect(computeDurationFromSteps(steps)).toBe(900)
  })
  it('steps with no duration_sec → 0 contribution each', () => {
    const steps = JSON.stringify([
      { type: 'interval', duration_type: 'distance', distance_m: 1000 },
    ])
    expect(computeDurationFromSteps(steps)).toBeNull()
  })
})

describe('test_computeDuration_repeat_group', () => {
  it('repeat×3 with 300s step → 900s', () => {
    const steps = JSON.stringify([
      {
        type: 'repeat',
        repeat_count: 3,
        steps: [{ type: 'interval', duration_sec: 300 }],
      },
    ])
    expect(computeDurationFromSteps(steps)).toBe(900)
  })

  it('repeat with multiple inner steps', () => {
    // 2 × (300 + 180) = 960
    const steps = JSON.stringify([
      {
        type: 'repeat',
        repeat_count: 2,
        steps: [
          { type: 'interval', duration_sec: 300 },
          { type: 'recovery', duration_sec: 180 },
        ],
      },
    ])
    expect(computeDurationFromSteps(steps)).toBe(960)
  })

  it('flat + repeat combined → correct total', () => {
    // 600 + 3×300 = 1500
    const steps = JSON.stringify([
      { type: 'warmup', duration_sec: 600 },
      {
        type: 'repeat',
        repeat_count: 3,
        steps: [{ type: 'interval', duration_sec: 300 }],
      },
    ])
    expect(computeDurationFromSteps(steps)).toBe(1500)
  })

  it('repeat_count missing → treated as 1', () => {
    const steps = JSON.stringify([
      {
        type: 'repeat',
        steps: [{ type: 'interval', duration_sec: 300 }],
      },
    ])
    expect(computeDurationFromSteps(steps)).toBe(300)
  })
})

// ─── computeDistanceFromSteps ──────────────────────────────────────────────

describe('test_computeDistance_nullish_input', () => {
  it('null → null', () => {
    expect(computeDistanceFromSteps(null)).toBeNull()
  })
  it('undefined → null', () => {
    expect(computeDistanceFromSteps(undefined)).toBeNull()
  })
})

describe('test_computeDistance_invalid_json', () => {
  it('invalid JSON → null (no throw)', () => {
    expect(computeDistanceFromSteps('not json')).toBeNull()
  })
})

describe('test_computeDistance_empty_array', () => {
  it('[] → null', () => {
    expect(computeDistanceFromSteps('[]')).toBeNull()
  })
})

describe('test_computeDistance_simple_steps', () => {
  it('two distance steps → sum in metres', () => {
    const steps = JSON.stringify([
      { type: 'warmup',   duration_type: 'distance', distance_m: 1000 },
      { type: 'cooldown', duration_type: 'distance', distance_m: 500  },
    ])
    expect(computeDistanceFromSteps(steps)).toBe(1500)
  })

  it('time-only steps (no distance_m) → null', () => {
    const steps = JSON.stringify([
      { type: 'warmup', duration_type: 'time', duration_sec: 600 },
    ])
    expect(computeDistanceFromSteps(steps)).toBeNull()
  })
})

describe('test_computeDistance_repeat_group', () => {
  it('repeat×4 with 500m step → 2000m', () => {
    const steps = JSON.stringify([
      {
        type: 'repeat',
        repeat_count: 4,
        steps: [{ type: 'interval', distance_m: 500 }],
      },
    ])
    expect(computeDistanceFromSteps(steps)).toBe(2000)
  })

  it('flat distance + repeat → correct total', () => {
    // 1000 + 6×400 = 3400
    const steps = JSON.stringify([
      { type: 'warmup', distance_m: 1000 },
      {
        type: 'repeat',
        repeat_count: 6,
        steps: [{ type: 'interval', distance_m: 400 }],
      },
    ])
    expect(computeDistanceFromSteps(steps)).toBe(3400)
  })
})

// ─── formatClock ───────────────────────────────────────────────────────────

describe('test_formatClock_sub_hour', () => {
  it('0s → "0:00"', () => {
    expect(formatClock(0)).toBe('0:00')
  })
  it('60s → "1:00"', () => {
    expect(formatClock(60)).toBe('1:00')
  })
  it('65s → "1:05" (seconds zero-padded)', () => {
    expect(formatClock(65)).toBe('1:05')
  })
  it('1680s (28 min) → "28:00"', () => {
    expect(formatClock(1680)).toBe('28:00')
  })
  it('2700s (45 min) → "45:00"', () => {
    expect(formatClock(2700)).toBe('45:00')
  })
  it('3599s → "59:59"', () => {
    expect(formatClock(3599)).toBe('59:59')
  })
})

describe('test_formatClock_with_hours', () => {
  it('3600s (1h) → "1:00:00"', () => {
    expect(formatClock(3600)).toBe('1:00:00')
  })
  it('4200s (1h10m) → "1:10:00"', () => {
    expect(formatClock(4200)).toBe('1:10:00')
  })
  it('3661s → "1:01:01"', () => {
    expect(formatClock(3661)).toBe('1:01:01')
  })
  it('minutes zero-padded when < 10', () => {
    expect(formatClock(3660)).toBe('1:01:00')
  })
})

// ─── formatKm ──────────────────────────────────────────────────────────────

describe('test_formatKm', () => {
  it('1000m → "1.0 km"', () => {
    expect(formatKm(1000)).toBe('1.0 km')
  })
  it('1500m → "1.5 km"', () => {
    expect(formatKm(1500)).toBe('1.5 km')
  })
  it('500m → "0.5 km"', () => {
    expect(formatKm(500)).toBe('0.5 km')
  })
  it('12500m → "12.5 km"', () => {
    expect(formatKm(12500)).toBe('12.5 km')
  })
  it('100m → "0.1 km" (1 decimal place)', () => {
    expect(formatKm(100)).toBe('0.1 km')
  })
})

import { describe, it, expect } from 'vitest'
import { computeCompliance } from './compliance'

describe('computeCompliance', () => {
  it('returns on_target when actual within 20% of planned duration', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      { duration_sec: 1900, distance_m: 5000 }
    )
    expect(result.level).toBe('on_target')
    expect(result.metric).toBe('duration')
  })

  it('returns close when actual 30% over planned', () => {
    const result = computeCompliance(
      { duration_sec: 1000, distance_m: null },
      { duration_sec: 1350, distance_m: 4000 }
    )
    expect(result.level).toBe('close')
    expect(result.direction).toBe('over')
  })

  it('returns off_target when actual >50% under planned', () => {
    const result = computeCompliance(
      { duration_sec: 3600, distance_m: null },
      { duration_sec: 1000, distance_m: 3000 }
    )
    expect(result.level).toBe('off_target')
    expect(result.direction).toBe('under')
  })

  it('falls back to distance when duration is null', () => {
    const result = computeCompliance(
      { duration_sec: null, distance_m: 10000 },
      { duration_sec: 2000, distance_m: 9500 }
    )
    expect(result.level).toBe('on_target')
    expect(result.metric).toBe('distance')
  })

  it('returns completed_no_plan when both planned metrics null', () => {
    const result = computeCompliance(
      { duration_sec: null, distance_m: null },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('completed_no_plan')
    expect(result.percentage).toBeNull()
  })

  it('treats zero planned values as null', () => {
    const result = computeCompliance(
      { duration_sec: 0, distance_m: 0 },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('completed_no_plan')
  })

  it('returns unplanned when planned is null', () => {
    const result = computeCompliance(
      null,
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.level).toBe('unplanned')
  })

  it('returns missed when actual is null', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      null
    )
    expect(result.level).toBe('missed')
  })

  it('percentage is 100 for exact match', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: null },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.percentage).toBe(100)
    expect(result.direction).toBeNull()
  })

  it('returns on_target at exactly 20% boundary', () => {
    const result = computeCompliance(
      { duration_sec: 1000, distance_m: null },
      { duration_sec: 1200, distance_m: 3000 }
    )
    expect(result.level).toBe('on_target')
    expect(result.percentage).toBe(120)
  })

  it('returns close at 21% over', () => {
    const result = computeCompliance(
      { duration_sec: 1000, distance_m: null },
      { duration_sec: 1210, distance_m: 3000 }
    )
    expect(result.level).toBe('close')
  })

  it('returns off_target at exactly 51% under', () => {
    const result = computeCompliance(
      { duration_sec: 1000, distance_m: null },
      { duration_sec: 490, distance_m: 1500 }
    )
    expect(result.level).toBe('off_target')
  })

  it('prefers duration over distance when both present', () => {
    const result = computeCompliance(
      { duration_sec: 1800, distance_m: 10000 },
      { duration_sec: 1800, distance_m: 5000 }
    )
    expect(result.metric).toBe('duration')
    expect(result.level).toBe('on_target')
  })
})

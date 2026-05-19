/// <reference types="vitest" />
import { describe, it, expect } from 'vitest'
import { buildStrengthPrompt } from '../StrengthPromptBuilder'
import type { GarminActivity } from '../../../api/types'

const noActivity: GarminActivity[] = []

describe('buildStrengthPrompt', () => {
  it('includes training days in prompt', () => {
    const p = buildStrengthPrompt({
      days: ['Monday', 'Wednesday', 'Friday'],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Monday, Wednesday, Friday')
    expect(p).toContain('3 days/week')
  })

  it('includes equipment list when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: ['Barbell', 'Dumbbells'],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Barbell, Dumbbells')
  })

  it('includes focus when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: 'Running-specific (glute/hip/core)',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Running-specific (glute/hip/core)')
  })

  it('includes health notes when non-empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: 'returning from knee injury',
      activities: noActivity,
    })
    expect(p).toContain('returning from knee injury')
  })

  it('omits health notes section when empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '   ',
      activities: noActivity,
    })
    expect(p).not.toContain('health')
    expect(p).not.toContain('shape')
  })

  it('includes recent strength activities in prompt', () => {
    const acts: GarminActivity[] = [{
      id: 1,
      garmin_activity_id: 'g1',
      activity_type: 'strength_training',
      name: 'Strength Training',
      start_time: '2026-06-01T08:00:00',
      date: '2026-06-01',
      duration_sec: 2700,
      distance_m: 0,
      avg_hr: 120,
      max_hr: null,
      avg_pace_sec_per_km: null,
      calories: null,
    }]
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: acts,
    })
    expect(p).toContain('2026-06-01')
    expect(p).toContain('45min')
    expect(p).toContain('Recent Training')
  })

  it('omits activity section when no activities', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).not.toContain('Recent Training')
  })

  it('always includes the strength shorthand grammar', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Squat 3x5@80kg')
    expect(p).toContain('RPE')
    expect(p).toContain('exercise catalog')
    expect(p).toContain('strength_plan.csv')
  })

  it('uses placeholders when no days or equipment selected', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('[your training days]')
    expect(p).toContain('[any equipment]')
  })
})

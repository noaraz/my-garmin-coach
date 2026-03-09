import type { StepType, WorkoutStep, RepeatGroup } from '../api/types'

export function makeStep(type: StepType): WorkoutStep {
  const defaults: Record<StepType, Partial<WorkoutStep>> = {
    warmup:   { duration_sec: 600,  target_type: 'pace_zone', zone: 2 },
    interval: { duration_sec: 300,  target_type: 'pace_zone', zone: 4 },
    recovery: { duration_sec: 180,  target_type: 'open' },
    cooldown: { duration_sec: 600,  target_type: 'pace_zone', zone: 1 },
  }
  return {
    id: crypto.randomUUID(),
    type,
    duration_type: 'time',
    target_type: 'open',
    ...defaults[type],
  } as WorkoutStep
}

export function makeRepeatGroup(): RepeatGroup {
  return {
    id: crypto.randomUUID(),
    type: 'repeat',
    repeat_count: 3,
    steps: [],
  }
}

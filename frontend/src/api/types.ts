export interface Profile {
  id: number
  name: string
  max_hr: number | null
  resting_hr: number | null
  lthr: number | null
  threshold_pace: number | null
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  name?: string
  max_hr?: number
  resting_hr?: number
  lthr?: number
  threshold_pace?: number
}

export interface HRZone {
  id: number
  profile_id: number
  zone_number: number
  name: string
  lower_bpm: number
  upper_bpm: number
  calculation_method: string
  pct_lower: number
  pct_upper: number
}

export interface HRZoneCreate {
  zone_number: number
  name: string
  lower_bpm: number
  upper_bpm: number
  calculation_method: string
  pct_lower: number
  pct_upper: number
}

export interface PaceZone {
  id: number
  profile_id: number
  zone_number: number
  name: string
  lower_pace: number
  upper_pace: number
  calculation_method: string
  pct_lower: number
  pct_upper: number
}

export interface WorkoutTemplate {
  id: number
  name: string
  description: string | null
  sport_type: string
  estimated_duration_sec: number | null
  estimated_distance_m: number | null
  tags: string | null
  steps: string | null
  created_at: string
  updated_at: string
}

export interface ScheduledWorkout {
  id: number
  date: string
  workout_template_id: number | null
  resolved_steps: string | null
  garmin_workout_id: string | null
  sync_status: SyncStatus
  completed: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export type SyncStatus = 'pending' | 'synced' | 'modified' | 'failed'

export interface ScheduleCreate {
  template_id: number
  date: string
}

export interface SyncStatusItem {
  id: number
  date: string
  sync_status: SyncStatus
  garmin_workout_id: string | null
}

export interface SyncAllResponse {
  synced: number
  failed: number
}

// Local builder types (not from API — these live only in the frontend)
export type StepType = 'warmup' | 'interval' | 'recovery' | 'cooldown'

export interface WorkoutStep {
  id: string        // nanoid or crypto.randomUUID()
  type: StepType
  duration_type: 'time' | 'distance'
  duration_sec?: number     // used when duration_type='time'
  distance_m?: number       // used when duration_type='distance'
  target_type: 'hr_zone' | 'pace_zone' | 'open'
  zone?: number             // 1-5
  notes?: string
}

export interface RepeatGroup {
  id: string
  type: 'repeat'
  repeat_count: number
  steps: WorkoutStep[]
}

export type BuilderStep = WorkoutStep | RepeatGroup

export interface WorkoutTemplateCreate {
  name: string
  description?: string
  sport_type: string
  estimated_duration_sec?: number
  estimated_distance_m?: number
  tags?: string
  steps?: BuilderStep[]
}

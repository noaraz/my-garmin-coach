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
  training_plan_id: number | null
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

export interface GarminActivity {
  id: number
  garmin_activity_id: string
  activity_type: string
  name: string
  start_time: string
  date: string
  duration_sec: number
  distance_m: number
  avg_hr: number | null
  max_hr: number | null
  avg_pace_sec_per_km: number | null
  calories: number | null
}

export interface ScheduledWorkoutWithActivity extends ScheduledWorkout {
  matched_activity_id: number | null
  activity: GarminActivity | null
}

export interface CalendarResponse {
  workouts: ScheduledWorkoutWithActivity[]
  unplanned_activities: GarminActivity[]
}

export interface SyncAllResponse {
  synced: number
  failed: number
  activities_fetched: number
  activities_matched: number
  fetch_error: string | null
}

export interface GarminStatusResponse {
  connected: boolean
  credentials_stored: boolean
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

// Plan Coach types
export interface ValidateRow {
  row: number
  date: string
  name: string
  steps_spec: string
  sport_type: string
  valid: boolean
  error: string | null
  template_status?: 'new' | 'existing'
}

export interface WorkoutDiff {
  date: string
  name: string
  old_name?: string
  old_steps_spec?: string
  new_steps_spec?: string
}

export interface DiffResult {
  added: WorkoutDiff[]
  removed: WorkoutDiff[]
  changed: WorkoutDiff[]
  unchanged: WorkoutDiff[]
  completed_locked: WorkoutDiff[]
}

export interface ValidateResult {
  plan_id: number
  rows: ValidateRow[]
  diff: DiffResult | null
}

export interface CommitResult {
  plan_id: number
  name: string
  workout_count: number
  start_date: string
}

export interface ActivePlan {
  plan_id: number
  name: string
  source: string
  status: string
  start_date: string
  workout_count: number | null
}

export interface PlanWorkoutInput {
  date: string
  name: string
  steps_spec: string
  sport_type?: string
  description?: string
}

export interface PlanCoachMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface SendMessageRequest {
  content: string
}

export interface BootstrapResponse {
  invite_codes: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

import type {
  Profile, ProfileUpdate,
  HRZone, HRZoneCreate,
  PaceZone,
  WorkoutTemplate, WorkoutTemplateCreate,
  ScheduledWorkout, ScheduleCreate,
  SyncAllResponse, SyncStatusItem,
} from './types'

const BASE = '/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const fetchProfile = () => request<Profile>('/profile')
export const updateProfile = (data: ProfileUpdate) =>
  request<Profile>('/profile', { method: 'PUT', body: JSON.stringify(data) })

export const fetchHRZones = () => request<HRZone[]>('/zones/hr')
export const updateHRZones = (zones: HRZoneCreate[]) =>
  request<HRZone[]>('/zones/hr', { method: 'PUT', body: JSON.stringify(zones) })
export const recalculateHRZones = () =>
  request<HRZone[]>('/zones/hr/recalculate', { method: 'POST' })

export const fetchPaceZones = () => request<PaceZone[]>('/zones/pace')
export const recalculatePaceZones = () =>
  request<PaceZone[]>('/zones/pace/recalculate', { method: 'POST' })

export const fetchWorkoutTemplates = () => request<WorkoutTemplate[]>('/workouts')

export const createTemplate = (body: WorkoutTemplateCreate) =>
  request<WorkoutTemplate>('/workouts', { method: 'POST', body: JSON.stringify(body) })

export const updateTemplate = (id: number, body: Partial<WorkoutTemplateCreate>) =>
  request<WorkoutTemplate>(`/workouts/${id}`, { method: 'PUT', body: JSON.stringify(body) })

export const deleteTemplate = (id: number) =>
  request<void>(`/workouts/${id}`, { method: 'DELETE' })

export const fetchCalendarRange = (start: string, end: string) =>
  request<ScheduledWorkout[]>(`/calendar?start=${start}&end=${end}`)
export const scheduleWorkout = (body: ScheduleCreate) =>
  request<ScheduledWorkout>('/calendar', { method: 'POST', body: JSON.stringify(body) })
export const rescheduleWorkout = (id: number, date: string) =>
  request<ScheduledWorkout>(`/calendar/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ date }),
  })
export const unscheduleWorkout = (id: number) =>
  request<void>(`/calendar/${id}`, { method: 'DELETE' })

export const syncAll = () =>
  request<SyncAllResponse>('/sync/all', { method: 'POST' })
export const syncOne = (id: number) =>
  request<SyncStatusItem>(`/sync/${id}`, { method: 'POST' })
export const fetchSyncStatus = () =>
  request<SyncStatusItem[]>('/sync/status')

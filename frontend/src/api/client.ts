import type {
  Profile, ProfileUpdate,
  HRZone, HRZoneCreate,
  PaceZone,
  WorkoutTemplate, WorkoutTemplateCreate,
  ScheduledWorkout, ScheduleCreate,
  SyncAllResponse, SyncStatusItem,
  GarminStatusResponse,
  BootstrapResponse,
} from './types'

const BASE = '/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader, ...options.headers },
    ...options,
  })

  if (res.status === 401) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Only redirect if this was an authenticated request (token expired / revoked).
    // Auth endpoints (login, register) have no token — let the error propagate so
    // the form can display "Invalid credentials" instead of silently reloading.
    if (token) {
      window.location.href = '/login'
      return undefined as T
    }
  }

  if (!res.ok) {
    let message: string
    try {
      const body = await res.json() as { detail?: string }
      message = body.detail ?? JSON.stringify(body)
    } catch {
      message = await res.text()
    }
    throw new Error(`${res.status}: ${message}`)
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

export const fetchWorkoutTemplate = (id: number) =>
  request<WorkoutTemplate>(`/workouts/${id}`)

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

export const loginUser = (email: string, password: string) =>
  request<{ access_token: string; refresh_token: string; token_type: string }>(
    '/auth/login',
    { method: 'POST', body: JSON.stringify({ email, password }) }
  )

export const registerUser = (email: string, password: string, invite_code: string) =>
  request<{ id: number; email: string }>(
    '/auth/register',
    { method: 'POST', body: JSON.stringify({ email, password, invite_code }) }
  )

export const fetchMe = () =>
  request<{ id: number; email: string; is_active: boolean; is_admin: boolean }>('/auth/me')

export const getGarminStatus = () =>
  request<GarminStatusResponse>('/garmin/status')

export const connectGarmin = (email: string, password: string) =>
  request<GarminStatusResponse>('/garmin/connect', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const disconnectGarmin = () =>
  request<GarminStatusResponse>('/garmin/disconnect', { method: 'POST' })

export const bootstrapAdmin = (setupToken: string, email: string, password: string) =>
  request<BootstrapResponse>('/auth/bootstrap', {
    method: 'POST',
    body: JSON.stringify({ setup_token: setupToken, email, password }),
  })

export const createInvite = () =>
  request<{ code: string }>('/auth/invite', { method: 'POST' })

export const resetAdmins = (setupToken: string) =>
  request<{ deleted: number }>('/auth/reset-admins', {
    method: 'POST',
    body: JSON.stringify({ setup_token: setupToken }),
  })

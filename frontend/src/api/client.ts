import type {
  Profile, ProfileUpdate,
  HRZone, HRZoneCreate,
  PaceZone,
  WorkoutTemplate, WorkoutTemplateCreate,
  ScheduledWorkout, ScheduleCreate,
  CalendarResponse, ScheduledWorkoutWithActivity,
  SyncAllResponse, SyncStatusItem,
  GarminStatusResponse,
  BootstrapResponse,
  TokenResponse,
  ValidateResult, CommitResult, ActivePlan, PlanWorkoutInput,
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
      const body = await res.json() as { detail?: string | Array<{ msg: string }> | unknown }
      if (Array.isArray(body.detail)) {
        message = body.detail.map(e => e.msg).join(', ')
      } else if (typeof body.detail === 'string') {
        message = body.detail
      } else {
        message = JSON.stringify(body.detail ?? body)
      }
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
  request<CalendarResponse>(`/calendar?start=${start}&end=${end}`)
export const scheduleWorkout = (body: ScheduleCreate) =>
  request<ScheduledWorkout>('/calendar', { method: 'POST', body: JSON.stringify(body) })
export const rescheduleWorkout = (id: number, date: string) =>
  request<ScheduledWorkout>(`/calendar/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ date }),
  })
export const updateWorkoutNotes = (id: number, notes: string) =>
  request<ScheduledWorkout>(`/calendar/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ notes }),
  })
export const unscheduleWorkout = (id: number) =>
  request<void>(`/calendar/${id}`, { method: 'DELETE' })

export const pairActivity = (scheduledId: number, activityId: number) =>
  request<ScheduledWorkoutWithActivity>(`/calendar/${scheduledId}/pair/${activityId}`, { method: 'POST' })
export const unpairActivity = (scheduledId: number) =>
  request<ScheduledWorkoutWithActivity>(`/calendar/${scheduledId}/unpair`, { method: 'POST' })

export const syncAll = () =>
  request<SyncAllResponse>('/sync/all', { method: 'POST' })
export const syncOne = (id: number) =>
  request<SyncStatusItem>(`/sync/${id}`, { method: 'POST' })
export const fetchSyncStatus = () =>
  request<SyncStatusItem[]>('/sync/status')

export const googleAuth = (accessToken: string, inviteCode?: string) =>
  request<TokenResponse>('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ access_token: accessToken, invite_code: inviteCode ?? null }),
  })

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

export const bootstrapAdmin = (setupToken: string, googleAccessToken: string) =>
  request<BootstrapResponse>('/auth/bootstrap', {
    method: 'POST',
    body: JSON.stringify({ setup_token: setupToken, google_access_token: googleAccessToken }),
  })

export const createInvite = () =>
  request<{ code: string }>('/auth/invite', { method: 'POST' })

export const resetAdmins = (setupToken: string) =>
  request<{ deleted: number }>('/auth/reset-admins', {
    method: 'POST',
    body: JSON.stringify({ setup_token: setupToken }),
  })

// Plan Coach
export const validatePlan = (name: string, workouts: PlanWorkoutInput[]) =>
  request<ValidateResult>('/plans/validate', {
    method: 'POST',
    body: JSON.stringify({ name, source: 'csv', workouts }),
  })

export const commitPlan = (planId: number) =>
  request<CommitResult>(`/plans/${planId}/commit`, { method: 'POST' })

export const getActivePlan = () =>
  request<ActivePlan | null>('/plans/active')

export const deletePlan = (planId: number) =>
  request<void>(`/plans/${planId}`, { method: 'DELETE' })

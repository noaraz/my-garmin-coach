import type {
  Profile, ProfileUpdate,
  HRZone, HRZoneCreate,
  PaceZone,
  WorkoutTemplate, WorkoutTemplateCreate,
  ScheduledWorkout, ScheduleCreate,
  CalendarResponse, ScheduledWorkoutWithActivity,
  SyncAllResponse, SyncStatusItem,
  GarminStatusResponse, GarminActivity,
  BootstrapResponse,
  TokenResponse,
  ValidateResult, CommitResult, ActivePlan, PlanWorkoutInput,
  PlanCoachMessage,
} from './types'

const BASE = '/api/v1'

// Singleton promise: if a refresh is already in flight, all callers share it.
// Prevents concurrent 401s from each independently rotating the token, which
// would cause the second rotation to trigger theft detection (revoked token reuse).
let _refreshPromise: Promise<boolean> | null = null

export async function tryRefreshToken(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = _doRefresh().finally(() => { _refreshPromise = null })
  return _refreshPromise
}

async function _doRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })

    if (!res.ok) {
      return false
    }

    const data = await res.json() as TokenResponse
    localStorage.setItem('access_token', data.access_token)
    return true
  } catch {
    return false
  }
}

async function request<T>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
  const token = localStorage.getItem('access_token')
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader, ...options.headers },
    credentials: 'include',
    ...options,
  })

  if (res.status === 401) {
    // Only redirect if this was an authenticated request (token expired / revoked).
    // Auth endpoints (login, register) have no token — let the error propagate so
    // the form can display "Invalid credentials" instead of silently reloading.
    if (token && !retried) {
      // Try to refresh the token
      const refreshed = await tryRefreshToken()
      if (refreshed) {
        // Retry the original request with the new token
        return request<T>(path, options, true)
      }
    }

    // Refresh failed or already retried — clear tokens and redirect
    if (token) {
      localStorage.removeItem('access_token')
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
export const refreshActivity = (id: number) =>
  request<GarminActivity>(`/calendar/activities/${id}/refresh`, { method: 'POST' })

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

export const getChatHistory = () =>
  request<PlanCoachMessage[]>('/plans/chat/history')

export const sendChatMessage = (content: string) =>
  request<PlanCoachMessage>('/plans/chat/message', {
    method: 'POST',
    body: JSON.stringify({ content }),
  })

export async function logout(): Promise<void> {
  try {
    await fetch(`${BASE}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
  } catch {
    // Best-effort — clear localStorage regardless
  }
  localStorage.removeItem('access_token')
}

export async function logoutAll(): Promise<void> {
  const token = localStorage.getItem('access_token')
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  await fetch(`${BASE}/auth/logout-all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader },
    credentials: 'include',
  })
}

export async function exportActivities(start: string, end: string): Promise<void> {
  const token = localStorage.getItem('access_token')
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  const res = await fetch(
    `${BASE}/calendar/activities/export?start=${start}&end=${end}`,
    { headers: { ...authHeader }, credentials: 'include' }
  )
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `garmin-export-${start}-${end}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 100)
}

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchProfile, fetchHRZones, fetchCalendarRange,
  scheduleWorkout, rescheduleWorkout, syncAll,
  tryRefreshToken, logout, logoutAll,
} from '../api/client'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
  localStorage.clear()
  delete (window as { location?: unknown }).location
  ;(window as { location: Partial<Location> }).location = { href: '' } as Location
})

afterEach(() => {
  vi.restoreAllMocks()
})

function mockResponse(data: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  })
}

describe('test_fetchProfile', () => {
  it('mock GET → profile object', async () => {
    const profile = { id: 1, name: 'Athlete', max_hr: 185, lthr: 162, threshold_pace: 270 }
    mockResponse(profile)
    const result = await fetchProfile()
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/profile', expect.objectContaining({ headers: expect.any(Object) }))
    expect(result.id).toBe(1)
    expect(result.lthr).toBe(162)
  })
})

describe('test_fetchHRZones', () => {
  it('mock GET → 5 zones', async () => {
    const zones = Array.from({ length: 5 }, (_, i) => ({
      id: i + 1, profile_id: 1, zone_number: i + 1,
      name: `Z${i + 1}`, lower_bpm: 100 + i * 20, upper_bpm: 120 + i * 20,
      calculation_method: 'coggan', pct_lower: 0.6, pct_upper: 0.7,
    }))
    mockResponse(zones)
    const result = await fetchHRZones()
    expect(result).toHaveLength(5)
    expect(result[0].zone_number).toBe(1)
  })
})

describe('test_fetchCalendarRange', () => {
  it('mock GET → workout list', async () => {
    const workouts = [
      { id: 1, date: '2026-03-09', sync_status: 'pending', completed: false },
      { id: 2, date: '2026-03-10', sync_status: 'synced', completed: false },
    ]
    mockResponse(workouts)
    const result = await fetchCalendarRange('2026-03-09', '2026-03-15')
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/calendar?start=2026-03-09&end=2026-03-15', expect.any(Object))
    expect(result).toHaveLength(2)
  })
})

describe('test_scheduleWorkout', () => {
  it('POST with date+template_id', async () => {
    const created = { id: 10, date: '2026-03-15', workout_template_id: 3, sync_status: 'pending' }
    mockResponse(created, 201)
    const result = await scheduleWorkout({ template_id: 3, date: '2026-03-15' })
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/calendar',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ template_id: 3, date: '2026-03-15' }) })
    )
    expect(result.id).toBe(10)
  })
})

describe('test_rescheduleWorkout', () => {
  it('PATCH with new date', async () => {
    const updated = { id: 5, date: '2026-03-20', sync_status: 'modified' }
    mockResponse(updated)
    await rescheduleWorkout(5, '2026-03-20')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/calendar/5',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ date: '2026-03-20' }) })
    )
  })
})

describe('test_triggerSync', () => {
  it('POST sync', async () => {
    mockResponse({ synced: 3, failed: 0 })
    const result = await syncAll()
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/sync/all', expect.objectContaining({ method: 'POST' }))
    expect(result.synced).toBe(3)
  })
})

describe('test_handles_network_error', () => {
  it('mock failure → error thrown', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'Internal Server Error' })
    await expect(fetchProfile()).rejects.toThrow('500:')
  })
})

describe('tryRefreshToken', () => {
  it('tryRefreshToken_concurrent_onlyOneRequest', async () => {
    // Two concurrent calls should result in only one fetch to /auth/refresh
    mockResponse({ access_token: 'new-token', token_type: 'bearer' })

    const [r1, r2] = await Promise.all([tryRefreshToken(), tryRefreshToken()])

    expect(r1).toBe(true)
    expect(r2).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(1)  // singleton — only one request
    expect(localStorage.getItem('access_token')).toBe('new-token')
  })

  it('tryRefreshToken_success_storesNewToken', async () => {
    mockResponse({ access_token: 'new-token', token_type: 'bearer' })

    const result = await tryRefreshToken()

    expect(result).toBe(true)
    expect(localStorage.getItem('access_token')).toBe('new-token')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/auth/refresh',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      })
    )
  })

  it('tryRefreshToken_failure_returnsFalse', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Token expired' }),
      text: async () => JSON.stringify({ detail: 'Token expired' }),
    })

    const result = await tryRefreshToken()

    expect(result).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

describe('401 retry behavior', () => {
  it('client_401_triesToRefresh_thenRetries', async () => {
    localStorage.setItem('access_token', 'old-token')

    let callCount = 0
    mockFetch.mockImplementation(() => {
      callCount++
      if (callCount === 1) {
        // First call to /profile returns 401
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Unauthorized' }),
          text: async () => JSON.stringify({ detail: 'Unauthorized' }),
        })
      } else if (callCount === 2) {
        // Second call to /auth/refresh succeeds
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access_token: 'new-token', token_type: 'bearer' }),
          text: async () => JSON.stringify({ access_token: 'new-token', token_type: 'bearer' }),
        })
      } else {
        // Third call to /profile succeeds
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 1, name: 'Test' }),
          text: async () => JSON.stringify({ id: 1, name: 'Test' }),
        })
      }
    })

    const profile = await fetchProfile()

    expect(profile).toEqual({ id: 1, name: 'Test' })
    expect(mockFetch).toHaveBeenCalledTimes(3)
    expect(localStorage.getItem('access_token')).toBe('new-token')
  })

  it('client_401_refreshFails_redirectsToLogin', async () => {
    localStorage.setItem('access_token', 'old-token')

    let callCount = 0
    mockFetch.mockImplementation(() => {
      callCount++
      if (callCount === 1) {
        // First call to /profile returns 401
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Unauthorized' }),
          text: async () => JSON.stringify({ detail: 'Unauthorized' }),
        })
      } else {
        // Second call to /auth/refresh fails
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Refresh token expired' }),
          text: async () => JSON.stringify({ detail: 'Refresh token expired' }),
        })
      }
    })

    // Should not throw, but redirect
    await fetchProfile()

    expect(window.location.href).toBe('/login')
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('client_401_noInfiniteRetry', async () => {
    localStorage.setItem('access_token', 'old-token')

    let callCount = 0
    mockFetch.mockImplementation(() => {
      callCount++
      if (callCount === 1) {
        // First call to /profile returns 401
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Unauthorized' }),
          text: async () => JSON.stringify({ detail: 'Unauthorized' }),
        })
      } else if (callCount === 2) {
        // Second call to /auth/refresh succeeds
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access_token: 'new-token', token_type: 'bearer' }),
          text: async () => JSON.stringify({ access_token: 'new-token', token_type: 'bearer' }),
        })
      } else {
        // Third call (retry) to /profile STILL returns 401 (token invalid)
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Unauthorized' }),
          text: async () => JSON.stringify({ detail: 'Unauthorized' }),
        })
      }
    })

    await fetchProfile()

    // Should redirect, not retry infinitely
    expect(mockFetch).toHaveBeenCalledTimes(3)
    expect(window.location.href).toBe('/login')
  })
})

describe('logout', () => {
  it('logout_callsBackendEndpoint', async () => {
    localStorage.setItem('access_token', 'token')
    mockResponse({ ok: true })

    await logout()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      })
    )
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

describe('logoutAll', () => {
  it('logoutAll_callsBackendEndpoint', async () => {
    localStorage.setItem('access_token', 'token')
    mockResponse({ revoked: 3 })

    await logoutAll()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/auth/logout-all',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      })
    )
  })
})

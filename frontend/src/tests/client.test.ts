import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchProfile, fetchHRZones, fetchCalendarRange,
  scheduleWorkout, rescheduleWorkout, syncAll,
} from '../api/client'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => { mockFetch.mockReset() })

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

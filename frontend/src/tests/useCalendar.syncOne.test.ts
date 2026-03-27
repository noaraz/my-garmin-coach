import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCalendar } from '../hooks/useCalendar'

const { mockSyncOne, mockFetchCalendarRange } = vi.hoisted(() => ({
  mockSyncOne: vi.fn(),
  mockFetchCalendarRange: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    syncOne: mockSyncOne,
    fetchCalendarRange: mockFetchCalendarRange,
  }
})

const defaultCalendarResponse = {
  workouts: [],
  unplanned_activities: [],
}

const syncStatusItem = {
  id: 5,
  date: '2026-03-30',
  sync_status: 'synced' as const,
  garmin_workout_id: 'G999',
}

beforeEach(() => {
  mockFetchCalendarRange.mockResolvedValue(defaultCalendarResponse)
  mockSyncOne.mockResolvedValue(syncStatusItem)
})

describe('useCalendar.syncOneWorkout', () => {
  it('calls syncOne with id, refetches calendar range, and returns SyncStatusItem', async () => {
    const start = new Date(2026, 2, 24)
    const end = new Date(2026, 2, 30)
    const { result } = renderHook(() => useCalendar(start, end))

    // Wait for initial load
    await act(async () => {})

    mockFetchCalendarRange.mockClear()

    let returned: unknown
    await act(async () => {
      returned = await result.current.syncOneWorkout(5)
    })

    expect(mockSyncOne).toHaveBeenCalledWith(5)
    expect(mockFetchCalendarRange).toHaveBeenCalledOnce()
    expect(returned).toEqual(syncStatusItem)
  })
})

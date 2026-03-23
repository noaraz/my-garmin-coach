import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { GarminStatusProvider } from '../contexts/GarminStatusContext'
import { ZonesStatusProvider } from '../contexts/ZonesStatusContext'
import { TodayPage } from '../pages/TodayPage'
import type { WorkoutTemplate } from '../api/types'

const now = new Date()
const TODAY = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

const mockEasyRunTemplate: WorkoutTemplate = {
  id: 10,
  name: 'Easy Run',
  description: '45min easy',
  sport_type: 'running',
  estimated_duration_sec: 2700,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
}

// Mock API
const { mockFetchCalendar, mockGetGarminStatus, mockFetchProfile, mockFetchTemplates } = vi.hoisted(() => ({
  mockFetchCalendar: vi.fn().mockResolvedValue({ workouts: [], unplanned_activities: [] }),
  mockGetGarminStatus: vi.fn().mockResolvedValue({ connected: true }),
  mockFetchProfile: vi.fn().mockResolvedValue({ threshold_pace: 300 }),
  mockFetchTemplates: vi.fn().mockResolvedValue([]),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchCalendarRange: mockFetchCalendar,
    getGarminStatus: mockGetGarminStatus,
    fetchProfile: mockFetchProfile,
    fetchWorkoutTemplates: mockFetchTemplates,
  }
})

const renderPage = () =>
  render(
    <MemoryRouter>
      <GarminStatusProvider>
        <ZonesStatusProvider>
          <TodayPage />
        </ZonesStatusProvider>
      </GarminStatusProvider>
    </MemoryRouter>
  )

describe('TodayPage', () => {
  beforeEach(() => {
    mockFetchCalendar.mockReset()
    mockFetchCalendar.mockResolvedValue({ workouts: [], unplanned_activities: [] })
    mockGetGarminStatus.mockReset()
    mockGetGarminStatus.mockResolvedValue({ connected: true })
    mockFetchProfile.mockReset()
    mockFetchProfile.mockResolvedValue({ threshold_pace: 300 })
    mockFetchTemplates.mockReset()
    mockFetchTemplates.mockResolvedValue([])
  })

  it('TodayPage_renders_pageHeader', async () => {
    renderPage()
    expect(await screen.findByText('Today')).toBeInTheDocument()
  })

  it('TodayPage_renders_weekStrip', async () => {
    renderPage()
    // Week strip has 7 day labels (M T W T F S S)
    await waitFor(() => {
      expect(screen.getAllByText(/^[MTWFS]$/).length).toBeGreaterThanOrEqual(5)
    })
  })

  it('TodayPage_withNoWorkout_showsRestDay', async () => {
    renderPage()
    expect(await screen.findByText(/rest day/i)).toBeInTheDocument()
  })

  it('TodayPage_withWorkout_showsHeroCard', async () => {
    mockFetchCalendar.mockResolvedValue({
      workouts: [{
        id: 1,
        date: TODAY,
        workout_template_id: 10,
        training_plan_id: null,
        resolved_steps: null,
        garmin_workout_id: null,
        sync_status: 'pending',
        completed: false,
        notes: null,
        created_at: TODAY,
        updated_at: TODAY,
        matched_activity_id: null,
        activity: null,
      }],
      unplanned_activities: [],
    })
    mockFetchTemplates.mockResolvedValue([mockEasyRunTemplate])
    renderPage()
    // Wait for both template name and duration to appear
    await waitFor(() => {
      expect(screen.getByText('Easy Run')).toBeInTheDocument()
      expect(screen.getByText('45:00')).toBeInTheDocument()
    })
  })

  it('TodayPage_garminConnected_showsGreenDot', async () => {
    renderPage()
    expect(await screen.findByLabelText(/garmin connected/i)).toBeInTheDocument()
  })
})

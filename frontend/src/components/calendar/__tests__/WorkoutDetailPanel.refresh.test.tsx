import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

const { mockRefreshActivity } = vi.hoisted(() => ({
  mockRefreshActivity: vi.fn(),
}))

vi.mock('../../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/client')>()
  return { ...actual, refreshActivity: mockRefreshActivity }
})

vi.mock('../../../hooks/useIsMobile', () => ({ useIsMobile: () => false }))

import { WorkoutDetailPanel } from '../WorkoutDetailPanel'
import type { GarminActivity } from '../../../api/types'

const mockActivity: GarminActivity = {
  id: 1,
  garmin_activity_id: 'garmin-42',
  activity_type: 'running',
  name: 'Morning Run',
  start_time: '2026-04-10T08:00:00',
  date: '2026-04-10',
  duration_sec: 3600,
  distance_m: 10000,
  avg_hr: 145,
  max_hr: 170,
  avg_pace_sec_per_km: 360,
  calories: 500,
}

const noop = () => {}
const noopAsync = async () => {}

const defaultProps = {
  onClose: noop,
  onReschedule: noopAsync,
  onRemove: noopAsync,
  onUnpair: noopAsync,
  onUpdateNotes: noopAsync,
  onNavigateToBuilder: noop,
}

describe('WorkoutDetailPanel — RefreshButton', () => {
  beforeEach(() => {
    mockRefreshActivity.mockReset()
  })

  it('renders a Refresh button for an unplanned activity', () => {
    render(
      <MemoryRouter>
        <WorkoutDetailPanel
          {...defaultProps}
          workout={null}
          activity={mockActivity}
          onRefreshActivity={noop}
        />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: /refresh from garmin/i })).toBeInTheDocument()
  })

  it('shows Refreshing… and is disabled while in flight', async () => {
    mockRefreshActivity.mockReturnValue(new Promise(() => {}))

    render(
      <MemoryRouter>
        <WorkoutDetailPanel
          {...defaultProps}
          workout={null}
          activity={mockActivity}
          onRefreshActivity={noop}
        />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /refresh from garmin/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /refreshing/i })).toBeDisabled()
    })
  })

  it('calls onRefreshActivity with updated activity on success', async () => {
    const updated = { ...mockActivity, distance_m: 10200 }
    mockRefreshActivity.mockResolvedValue(updated)

    const onRefresh = vi.fn()
    render(
      <MemoryRouter>
        <WorkoutDetailPanel
          {...defaultProps}
          workout={null}
          activity={mockActivity}
          onRefreshActivity={onRefresh}
        />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /refresh from garmin/i }))

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalledWith(updated)
    })
  })

  it('re-enables the button after an error', async () => {
    mockRefreshActivity.mockRejectedValue(new Error('Garmin unavailable'))

    render(
      <MemoryRouter>
        <WorkoutDetailPanel
          {...defaultProps}
          workout={null}
          activity={mockActivity}
          onRefreshActivity={noop}
        />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /refresh from garmin/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /refresh from garmin/i })).not.toBeDisabled()
    })
  })
})

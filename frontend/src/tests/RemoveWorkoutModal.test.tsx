import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RemoveWorkoutModal } from '../components/calendar/RemoveWorkoutModal'

const defaultProps = {
  workoutName: 'Tempo Run',
  workoutDate: '2026-03-26',
  isSyncedToGarmin: false,
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
  isRemoving: false,
}

describe('RemoveWorkoutModal', () => {
  it('test_renders_workout_name_and_date', () => {
    render(<RemoveWorkoutModal {...defaultProps} />)

    expect(screen.getByText('Tempo Run')).toBeTruthy()
    expect(screen.getByText(/Mar 26, 2026/)).toBeTruthy()
  })

  it('test_shows_garmin_warning_when_synced', () => {
    render(<RemoveWorkoutModal {...defaultProps} isSyncedToGarmin={true} />)

    expect(screen.getByText(/will also be removed from Garmin/)).toBeTruthy()
  })

  it('test_hides_garmin_warning_when_not_synced', () => {
    render(<RemoveWorkoutModal {...defaultProps} isSyncedToGarmin={false} />)

    expect(screen.queryByText(/will also be removed from Garmin/)).toBeNull()
  })

  it('test_calls_onConfirm_when_remove_clicked', () => {
    const onConfirm = vi.fn()
    render(<RemoveWorkoutModal {...defaultProps} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('button', { name: /confirm remove/i }))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('test_calls_onCancel_when_cancel_clicked', () => {
    const onCancel = vi.fn()
    render(<RemoveWorkoutModal {...defaultProps} onCancel={onCancel} />)

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('test_calls_onCancel_when_backdrop_clicked', () => {
    const onCancel = vi.fn()
    render(<RemoveWorkoutModal {...defaultProps} onCancel={onCancel} />)

    fireEvent.click(screen.getByRole('dialog'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('test_shows_removing_state_and_disables_buttons', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <RemoveWorkoutModal
        {...defaultProps}
        isRemoving={true}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    )

    const confirmBtn = screen.getByRole('button', { name: /confirm remove/i })
    const cancelBtn = screen.getByRole('button', { name: /cancel/i })

    expect(confirmBtn).toBeDisabled()
    expect(cancelBtn).toBeDisabled()
    expect(confirmBtn.textContent).toContain('Removing')

    fireEvent.click(confirmBtn)
    fireEvent.click(cancelBtn)
    expect(onConfirm).not.toHaveBeenCalled()
    expect(onCancel).not.toHaveBeenCalled()
  })

  it('test_shows_cannot_be_undone_when_not_synced', () => {
    render(<RemoveWorkoutModal {...defaultProps} isSyncedToGarmin={false} />)

    expect(screen.getByText(/cannot be undone/)).toBeTruthy()
  })
})

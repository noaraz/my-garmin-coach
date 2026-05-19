import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { PlanCoachPage } from '../../pages/PlanCoachPage'

const { mockGetActivePlan } = vi.hoisted(() => ({
  mockGetActivePlan: vi.fn(),
}))

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>()
  return { ...actual, getActivePlan: mockGetActivePlan }
})

beforeEach(() => {
  mockGetActivePlan.mockResolvedValue(null)
})

describe('PlanCoachPage tab switcher', () => {
  it('renders Running tab selected by default', async () => {
    render(<MemoryRouter><PlanCoachPage /></MemoryRouter>)
    const running = screen.getByRole('tab', { name: /running/i })
    expect(running).toHaveAttribute('aria-selected', 'true')
    const strength = screen.getByRole('tab', { name: /strength/i })
    expect(strength).toHaveAttribute('aria-selected', 'false')
  })

  it('switches to Strength tab on click', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><PlanCoachPage /></MemoryRouter>)
    await user.click(screen.getByRole('tab', { name: /strength/i }))
    expect(screen.getByRole('tab', { name: /strength/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: /running/i })).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByText(/strength shorthand|exercise catalog/i)).toBeInTheDocument()
  })

  it('shows Running tab content by default', async () => {
    render(<MemoryRouter><PlanCoachPage /></MemoryRouter>)
    // Running tabpanel is present
    expect(screen.getByRole('tabpanel', { name: /running|plan sport/i })).toBeInTheDocument()
  })
})

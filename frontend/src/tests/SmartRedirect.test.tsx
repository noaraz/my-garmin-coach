import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { SmartRedirect } from '../components/SmartRedirect'

// Mock useIsMobile hook
const mockUseIsMobile = vi.fn()
vi.mock('../hooks/useIsMobile', () => ({
  useIsMobile: () => mockUseIsMobile(),
}))

// Mock Navigate component to track where it redirects
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => {
      mockNavigate(to)
      return <div data-testid="navigate" data-to={to}>Navigate to {to}</div>
    },
  }
})

describe('SmartRedirect', () => {
  beforeEach(() => {
    mockUseIsMobile.mockReset()
    mockNavigate.mockReset()
  })

  it('SmartRedirect_onDesktop_redirectsToCalendar', () => {
    mockUseIsMobile.mockReturnValue(false)
    render(
      <BrowserRouter>
        <SmartRedirect />
      </BrowserRouter>
    )
    expect(mockNavigate).toHaveBeenCalledWith('/calendar')
  })

  it('SmartRedirect_onMobile_redirectsToToday', () => {
    mockUseIsMobile.mockReturnValue(true)
    render(
      <BrowserRouter>
        <SmartRedirect />
      </BrowserRouter>
    )
    expect(mockNavigate).toHaveBeenCalledWith('/today')
  })
})

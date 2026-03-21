import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { BottomTabBar } from '../components/layout/BottomTabBar'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate, useLocation: () => ({ pathname: '/today' }) }
})

const renderBar = () =>
  render(<MemoryRouter><BottomTabBar /></MemoryRouter>)

describe('BottomTabBar', () => {
  it('BottomTabBar_renders_fiveTabs', () => {
    renderBar()
    expect(screen.getByLabelText('Today')).toBeInTheDocument()
    expect(screen.getByLabelText('Calendar')).toBeInTheDocument()
    expect(screen.getByLabelText('Library')).toBeInTheDocument()
    expect(screen.getByLabelText('Zones')).toBeInTheDocument()
    expect(screen.getByLabelText('More')).toBeInTheDocument()
  })

  it('BottomTabBar_clickCalendar_navigatesToCalendar', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('Calendar'))
    expect(mockNavigate).toHaveBeenCalledWith('/calendar')
  })

  it('BottomTabBar_clickMore_opensMoreSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    expect(screen.getByText('Builder')).toBeInTheDocument()
    expect(screen.getByText('Plan Coach')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Help')).toBeInTheDocument()
  })

  it('BottomTabBar_clickBackdrop_closesMoreSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    expect(screen.getByText('Builder')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('more-sheet-backdrop'))
    expect(screen.queryByText('Builder')).not.toBeInTheDocument()
  })

  it('BottomTabBar_clickMoreItem_navigatesAndClosesSheet', () => {
    renderBar()
    fireEvent.click(screen.getByLabelText('More'))
    fireEvent.click(screen.getByText('Settings'))
    expect(mockNavigate).toHaveBeenCalledWith('/settings')
    expect(screen.queryByText('Builder')).not.toBeInTheDocument()
  })
})

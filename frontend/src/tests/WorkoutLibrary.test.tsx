import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WorkoutLibrary } from '../components/library/WorkoutLibrary'
import { MemoryRouter } from 'react-router-dom'

const { mockDeleteTemplate, mockCreateTemplate, mockNavigate, mockTemplates } = vi.hoisted(() => {
  const templates = [
    { id: 1, name: 'Easy Run',        sport_type: 'running', estimated_duration_sec: 2700, estimated_distance_m: null, description: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Interval Session', sport_type: 'running', estimated_duration_sec: 3600, estimated_distance_m: null, description: null, tags: null, steps: null, created_at: '', updated_at: '' },
    { id: 3, name: 'Long Run',         sport_type: 'running', estimated_duration_sec: 5400, estimated_distance_m: null, description: null, tags: null, steps: null, created_at: '', updated_at: '' },
  ]
  return {
    mockDeleteTemplate: vi.fn(),
    mockCreateTemplate: vi.fn(),
    mockNavigate: vi.fn(),
    mockTemplates: templates,
  }
})

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchWorkoutTemplates: vi.fn().mockResolvedValue(mockTemplates),
    deleteTemplate: mockDeleteTemplate,
    createTemplate: mockCreateTemplate,
  }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

beforeEach(() => {
  mockDeleteTemplate.mockReset()
  mockCreateTemplate.mockReset()
  mockNavigate.mockReset()
})

function renderLibrary() {
  return render(<MemoryRouter><WorkoutLibrary /></MemoryRouter>)
}

describe('test_renders_list', () => {
  it('3 templates → 3 cards', async () => {
    renderLibrary()
    await waitFor(() => {
      expect(screen.getAllByTestId('template-card')).toHaveLength(3)
    })
  })
})

describe('test_search_filters', () => {
  it('type "interval" → only matching card shown', async () => {
    const user = userEvent.setup()
    renderLibrary()
    await waitFor(() => screen.getAllByTestId('template-card'))
    const searchInput = screen.getByRole('searchbox', { name: /search/i })
    await user.type(searchInput, 'interval')
    expect(screen.getAllByTestId('template-card')).toHaveLength(1)
    expect(screen.getByText('Interval Session')).toBeInTheDocument()
  })
})

describe('test_click_opens_builder', () => {
  it('click Edit on template → navigate to /builder?id=1', async () => {
    const user = userEvent.setup()
    renderLibrary()
    await waitFor(() => screen.getAllByTestId('template-card'))
    const editBtns = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editBtns[0])
    expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('/builder'))
  })
})

describe('test_schedule_opens_picker', () => {
  it('click Schedule → date picker shown', async () => {
    const user = userEvent.setup()
    renderLibrary()
    await waitFor(() => screen.getAllByTestId('template-card'))
    const scheduleBtns = screen.getAllByRole('button', { name: /schedule/i })
    await user.click(scheduleBtns[0])
    expect(screen.getByRole('dialog', { name: /schedule/i })).toBeInTheDocument()
  })
})

describe('test_delete', () => {
  it('click Delete → deleteTemplate called, card removed', async () => {
    const user = userEvent.setup()
    mockDeleteTemplate.mockResolvedValue(undefined)
    renderLibrary()
    await waitFor(() => screen.getAllByTestId('template-card'))
    const deleteBtns = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteBtns[0])
    await waitFor(() => {
      expect(mockDeleteTemplate).toHaveBeenCalledWith(1)
      expect(screen.getAllByTestId('template-card')).toHaveLength(2)
    })
  })
})

describe('test_duplicate', () => {
  it('click Duplicate → createTemplate called with same data', async () => {
    const user = userEvent.setup()
    mockCreateTemplate.mockResolvedValue({ ...mockTemplates[0], id: 99 })
    renderLibrary()
    await waitFor(() => screen.getAllByTestId('template-card'))
    const dupBtns = screen.getAllByRole('button', { name: /duplicate/i })
    await user.click(dupBtns[0])
    await waitFor(() => {
      expect(mockCreateTemplate).toHaveBeenCalledWith(
        expect.objectContaining({ name: expect.stringContaining('Easy Run') })
      )
    })
  })
})

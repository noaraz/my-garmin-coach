import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WorkoutLibrary } from '../components/library/WorkoutLibrary'
import { MemoryRouter } from 'react-router-dom'

const { mockDeleteTemplate, mockCreateTemplate, mockNavigate, mockTemplates, mockFetchTemplates } = vi.hoisted(() => {
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
    mockFetchTemplates: vi.fn().mockResolvedValue(templates),
  }
})

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchWorkoutTemplates: mockFetchTemplates,
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
  mockFetchTemplates.mockReset()
  mockFetchTemplates.mockResolvedValue(mockTemplates)
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

describe('test_template_card_clock_from_estimated', () => {
  it('estimated_duration_sec → shows clock format', async () => {
    renderLibrary()
    // Easy Run has 2700s = 45:00
    expect(await screen.findByText('45:00')).toBeInTheDocument()
  })
})

describe('test_template_card_clock_from_steps_fallback', () => {
  it('null estimated_duration_sec + steps JSON → computes clock', async () => {
    // 600 + 300 + 3×300 + 600 = 2400s = 40:00
    const stepsJson = JSON.stringify([
      { type: 'warmup',   duration_type: 'time', duration_sec: 600 },
      { type: 'interval', duration_type: 'time', duration_sec: 300 },
      { type: 'repeat', repeat_count: 3, steps: [{ type: 'interval', duration_sec: 300 }] },
      { type: 'cooldown', duration_type: 'time', duration_sec: 600 },
    ])
    mockFetchTemplates.mockResolvedValue([
      { id: 10, name: 'Step Calc Run', sport_type: 'running',
        estimated_duration_sec: null, estimated_distance_m: null,
        description: null, tags: null, steps: stepsJson,
        created_at: '', updated_at: '' },
    ])
    renderLibrary()
    expect(await screen.findByText('40:00')).toBeInTheDocument()
  })
})

describe('test_template_card_shows_distance', () => {
  it('estimated_distance_m → shows km alongside duration', async () => {
    mockFetchTemplates.mockResolvedValue([
      { id: 11, name: 'Distance Run', sport_type: 'running',
        estimated_duration_sec: 1800, estimated_distance_m: 10000,
        description: null, tags: null, steps: null,
        created_at: '', updated_at: '' },
    ])
    renderLibrary()
    expect(await screen.findByText('30:00')).toBeInTheDocument()
    expect(screen.getByText('10.0 km')).toBeInTheDocument()
  })
})

describe('test_template_card_no_summary_when_no_data', () => {
  it('null duration + null steps → no clock text', async () => {
    mockFetchTemplates.mockResolvedValue([
      { id: 12, name: 'Empty Run', sport_type: 'running',
        estimated_duration_sec: null, estimated_distance_m: null,
        description: null, tags: null, steps: null,
        created_at: '', updated_at: '' },
    ])
    renderLibrary()
    await screen.findByText('Empty Run')
    const card = screen.getByTestId('template-card')
    expect(card.textContent).not.toMatch(/\d+:\d{2}/)
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

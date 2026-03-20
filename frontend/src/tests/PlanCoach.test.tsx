import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ValidateResult, ValidateRow, ActivePlan, DiffResult, PlanCoachMessage } from '../api/types'

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const { mockValidatePlan, mockCommitPlan, mockGetActivePlan, mockDeletePlan, mockGetChatHistory, mockSendChatMessage, mockNavigate } = vi.hoisted(() => ({
  mockValidatePlan: vi.fn(),
  mockCommitPlan: vi.fn(),
  mockGetActivePlan: vi.fn(),
  mockDeletePlan: vi.fn(),
  mockGetChatHistory: vi.fn(),
  mockSendChatMessage: vi.fn(),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    validatePlan: mockValidatePlan,
    commitPlan: mockCommitPlan,
    getActivePlan: mockGetActivePlan,
    deletePlan: mockDeletePlan,
    getChatHistory: mockGetChatHistory,
    sendChatMessage: mockSendChatMessage,
  }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const validRow = (overrides: Partial<ValidateRow> = {}): ValidateRow => ({
  row: 1,
  date: '2026-04-07',
  name: 'Easy Run',
  steps_spec: '10m@Z1, 30m@Z2, 5m@Z1',
  sport_type: 'running',
  valid: true,
  error: null,
  ...overrides,
})

const invalidRow = (): ValidateRow => ({
  row: 2,
  date: '2026-04-08',
  name: 'Bad Workout',
  steps_spec: 'garbage',
  sport_type: 'running',
  valid: false,
  error: 'Unrecognised step token: "garbage"',
})

const successResult: ValidateResult = {
  plan_id: 42,
  rows: [validRow()],
  diff: null,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const renderPage = async () => {
  const { PlanCoachPage } = await import('../pages/PlanCoachPage')
  return render(
    <MemoryRouter>
      <PlanCoachPage />
    </MemoryRouter>
  )
}

const renderCsvTab = async () => {
  const { CsvImportTab } = await import('../components/plan-coach/CsvImportTab')
  return render(
    <MemoryRouter>
      <CsvImportTab />
    </MemoryRouter>
  )
}

const renderValidationTable = async (rows: ValidateRow[]) => {
  const { ValidationTable } = await import('../components/plan-coach/ValidationTable')
  return render(<ValidationTable rows={rows} />)
}

// ---------------------------------------------------------------------------
// LlmPromptTemplate
// ---------------------------------------------------------------------------

describe('LlmPromptTemplate', () => {
  it('renders step format reference', async () => {
    const { LlmPromptTemplate } = await import('../components/plan-coach/LlmPromptTemplate')
    render(<LlmPromptTemplate />)
    expect(screen.getByText(/CSV Format/i)).toBeInTheDocument()
    expect(screen.getByText(/steps_spec/i)).toBeInTheDocument()
  })

  it('shows copy button', async () => {
    const { LlmPromptTemplate } = await import('../components/plan-coach/LlmPromptTemplate')
    render(<LlmPromptTemplate />)
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// ValidationTable
// ---------------------------------------------------------------------------

describe('ValidationTable', () => {
  it('renders a valid row with checkmark', async () => {
    await renderValidationTable([validRow()])
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
    expect(screen.getByText('2026-04-07')).toBeInTheDocument()
    expect(screen.getByText('✓')).toBeInTheDocument()
  })

  it('renders an invalid row with error message', async () => {
    await renderValidationTable([invalidRow()])
    expect(screen.getByText('Bad Workout')).toBeInTheDocument()
    expect(screen.getByText(/unrecognised step token/i)).toBeInTheDocument()
  })

  it('renders mixed rows', async () => {
    await renderValidationTable([validRow(), invalidRow()])
    expect(screen.getAllByRole('row')).toHaveLength(3) // header + 2 data rows
  })
})

// ---------------------------------------------------------------------------
// CsvImportTab — file upload
// ---------------------------------------------------------------------------

describe('CsvImportTab file upload', () => {
  beforeEach(() => {
    mockValidatePlan.mockReset()
    mockCommitPlan.mockReset()
    mockGetActivePlan.mockReset()
    mockGetActivePlan.mockResolvedValue(null)
  })

  it('renders file input and validate button initially disabled', async () => {
    await renderCsvTab()
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeInTheDocument()
    const validateBtn = screen.getByRole('button', { name: /validate/i })
    expect(validateBtn).toBeDisabled()
  })

  it('shows validation results after successful upload', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue(successResult)
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec,sport_type\n2026-04-07,Easy Run,10m@Z1,running'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement

    await user.upload(input, file)

    const validateBtn = screen.getByRole('button', { name: /validate/i })
    await user.click(validateBtn)

    await waitFor(() => {
      expect(mockValidatePlan).toHaveBeenCalledTimes(1)
      expect(screen.getByText('Easy Run')).toBeInTheDocument()
    })
  })

  it('Import button disabled when validation has errors', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue({
      plan_id: 99,
      rows: [validRow(), invalidRow()],
      diff: null,
    })
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1\n2026-04-08,Bad,garbage'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    const validateBtn = screen.getByRole('button', { name: /validate/i })
    await user.click(validateBtn)

    await waitFor(() => {
      expect(screen.getByText('Bad Workout')).toBeInTheDocument()
    })

    const importBtn = screen.getByRole('button', { name: /import/i })
    expect(importBtn).toBeDisabled()
  })

  it('Import button enabled when all rows valid', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue(successResult)
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    const validateBtn = screen.getByRole('button', { name: /validate/i })
    await user.click(validateBtn)

    await waitFor(() => {
      const importBtn = screen.getByRole('button', { name: /import/i })
      expect(importBtn).not.toBeDisabled()
    })
  })

  it('calls commitPlan and navigates to /calendar on successful import', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue(successResult)
    mockCommitPlan.mockResolvedValue({ plan_id: 42, name: 'My Plan', workout_count: 1, start_date: '2026-04-07' })
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    const validateBtn = screen.getByRole('button', { name: /validate/i })
    await user.click(validateBtn)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import/i })).not.toBeDisabled()
    })

    const importBtn = screen.getByRole('button', { name: /import/i })
    await user.click(importBtn)

    await waitFor(() => {
      expect(mockCommitPlan).toHaveBeenCalledWith(42)
      expect(mockNavigate).toHaveBeenCalledWith('/calendar')
    })
  })
})

// ---------------------------------------------------------------------------
// PlanCoachPage — no active plan
// ---------------------------------------------------------------------------

describe('PlanCoachPage', () => {
  beforeEach(() => {
    mockGetActivePlan.mockReset()
    mockGetActivePlan.mockResolvedValue(null)
  })

  it('shows file input when no active plan', async () => {
    await renderPage()
    await waitFor(() => {
      expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Phase 3 — fixtures
// ---------------------------------------------------------------------------

const activePlan: ActivePlan = {
  plan_id: 7,
  name: 'HM April 2026',
  source: 'csv',
  status: 'active',
  start_date: '2026-04-07',
  workout_count: 48,
}

const diffResult: DiffResult = {
  added: [{ date: '2026-04-21', name: 'New Long Run' }],
  removed: [{ date: '2026-04-14', name: 'Old Tempo' }],
  changed: [{ date: '2026-04-07', name: 'Easy Run' }],
  unchanged: [],
  completed_locked: [],
}

// ---------------------------------------------------------------------------
// ActivePlanCard
// ---------------------------------------------------------------------------

describe('ActivePlanCard', () => {
  it('renders plan name and workout count', async () => {
    const { ActivePlanCard } = await import('../components/plan-coach/ActivePlanCard')
    render(<ActivePlanCard plan={activePlan} onUploadNew={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('HM April 2026')).toBeInTheDocument()
    expect(screen.getByText(/48 workouts/i)).toBeInTheDocument()
  })

  it('calls onUploadNew when Upload New Plan button clicked', async () => {
    const user = userEvent.setup()
    const { ActivePlanCard } = await import('../components/plan-coach/ActivePlanCard')
    const onUploadNew = vi.fn()
    render(<ActivePlanCard plan={activePlan} onUploadNew={onUploadNew} onDelete={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /upload or update plan/i }))
    expect(onUploadNew).toHaveBeenCalledTimes(1)
  })

  it('calls onDelete when Delete Plan button clicked', async () => {
    const user = userEvent.setup()
    const { ActivePlanCard } = await import('../components/plan-coach/ActivePlanCard')
    const onDelete = vi.fn()
    render(<ActivePlanCard plan={activePlan} onUploadNew={vi.fn()} onDelete={onDelete} />)
    await user.click(screen.getByRole('button', { name: /delete plan/i }))
    expect(onDelete).toHaveBeenCalledTimes(1)
  })
})

// ---------------------------------------------------------------------------
// DeletePlanModal
// ---------------------------------------------------------------------------

describe('DeletePlanModal', () => {
  it('renders plan name and workout count in warning', async () => {
    const { DeletePlanModal } = await import('../components/plan-coach/DeletePlanModal')
    render(
      <DeletePlanModal plan={activePlan} onConfirm={vi.fn()} onCancel={vi.fn()} isDeleting={false} />
    )
    expect(screen.getByText('HM April 2026')).toBeInTheDocument()
    expect(screen.getByText(/remove all 48 scheduled workouts/i)).toBeInTheDocument()
  })

  it('calls onConfirm when Delete Plan button clicked', async () => {
    const user = userEvent.setup()
    const { DeletePlanModal } = await import('../components/plan-coach/DeletePlanModal')
    const onConfirm = vi.fn()
    render(
      <DeletePlanModal plan={activePlan} onConfirm={onConfirm} onCancel={vi.fn()} isDeleting={false} />
    )
    await user.click(screen.getByRole('button', { name: /confirm delete/i }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when Cancel button clicked', async () => {
    const user = userEvent.setup()
    const { DeletePlanModal } = await import('../components/plan-coach/DeletePlanModal')
    const onCancel = vi.fn()
    render(
      <DeletePlanModal plan={activePlan} onConfirm={vi.fn()} onCancel={onCancel} isDeleting={false} />
    )
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables buttons when isDeleting is true', async () => {
    const { DeletePlanModal } = await import('../components/plan-coach/DeletePlanModal')
    render(
      <DeletePlanModal plan={activePlan} onConfirm={vi.fn()} onCancel={vi.fn()} isDeleting={true} />
    )
    expect(screen.getByRole('button', { name: /confirm delete/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
  })
})

// ---------------------------------------------------------------------------
// DiffTable
// ---------------------------------------------------------------------------

describe('DiffTable', () => {
  it('renders added, removed, and changed rows', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    render(<DiffTable diff={diffResult} />)
    expect(screen.getByText('New Long Run')).toBeInTheDocument()
    expect(screen.getByText('Old Tempo')).toBeInTheDocument()
    expect(screen.getByText('Easy Run')).toBeInTheDocument()
  })

  it('shows summary counts', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    render(<DiffTable diff={diffResult} />)
    expect(screen.getByText(/\+1 added/i)).toBeInTheDocument()
    expect(screen.getByText(/−1 removed/i)).toBeInTheDocument()
    expect(screen.getByText(/~1 changed/i)).toBeInTheDocument()
  })

  it('renders nothing when diff has no changes', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const { container } = render(<DiffTable diff={{ added: [], removed: [], changed: [], unchanged: [], completed_locked: [] }} />)
    expect(container.firstChild).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// PlanCoachPage — active plan state
// ---------------------------------------------------------------------------

describe('PlanCoachPage with active plan', () => {
  beforeEach(() => {
    mockGetActivePlan.mockReset()
    mockDeletePlan.mockReset()
    mockGetActivePlan.mockResolvedValue(activePlan)
  })

  // Helper: render page and return user event instance
  async function renderOnPlanTab() {
    const user = userEvent.setup()
    await renderPage()
    return user
  }

  it('shows ActivePlanCard when active plan exists', async () => {
    await renderOnPlanTab()
    await waitFor(() => {
      expect(screen.getByTestId('active-plan-card')).toBeInTheDocument()
    })
    expect(screen.getByText('HM April 2026')).toBeInTheDocument()
  })

  it('does not show file upload until Upload New Plan is clicked', async () => {
    await renderOnPlanTab()
    await waitFor(() => {
      expect(screen.getByTestId('active-plan-card')).toBeInTheDocument()
    })
    // File input hidden until Upload New Plan clicked
    expect(document.querySelector('input[type="file"]')).not.toBeInTheDocument()
  })

  it('shows file upload after clicking Upload New Plan', async () => {
    const user = await renderOnPlanTab()
    await waitFor(() => {
      expect(screen.getByTestId('active-plan-card')).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /upload or update plan/i }))
    expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
  })

  it('shows delete modal on Delete Plan click and calls deletePlan on confirm', async () => {
    const user = await renderOnPlanTab()
    mockDeletePlan.mockResolvedValue(undefined)
    await waitFor(() => {
      expect(screen.getByTestId('active-plan-card')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /delete plan/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    // Re-mock so that after delete, active plan is gone
    mockGetActivePlan.mockResolvedValue(null)
    await user.click(screen.getByRole('button', { name: /confirm delete/i }))
    await waitFor(() => {
      expect(mockDeletePlan).toHaveBeenCalledWith(7)
    })
  })
})

// ---------------------------------------------------------------------------
// CsvImportTab — diff flow (Phase 3)
// ---------------------------------------------------------------------------

describe('CsvImportTab diff flow', () => {
  beforeEach(() => {
    mockValidatePlan.mockReset()
    mockCommitPlan.mockReset()
    mockGetActivePlan.mockReset()
    mockGetActivePlan.mockResolvedValue(null)
  })

  it('shows DiffTable when validate returns a diff', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue({
      plan_id: 42,
      rows: [validRow()],
      diff: diffResult,
    })
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByTestId('diff-table')).toBeInTheDocument()
    })
    expect(screen.getByText('New Long Run')).toBeInTheDocument()
  })

  it('shows Apply Changes button label when diff is non-null', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue({
      plan_id: 42,
      rows: [validRow()],
      diff: diffResult,
    })
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /apply changes/i })).toBeInTheDocument()
    })
  })

  it('shows Import button label when diff is null', async () => {
    const user = userEvent.setup()
    mockValidatePlan.mockResolvedValue(successResult) // diff: null
    await renderCsvTab()

    const csvContent = 'date,name,steps_spec\n2026-04-07,Easy Run,10m@Z1'
    const file = new File([csvContent], 'plan.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, file)

    await user.click(screen.getByRole('button', { name: /validate/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import plan/i })).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Phase 4 — ChatTab fixtures
// ---------------------------------------------------------------------------

const makeMsg = (overrides: Partial<PlanCoachMessage> = {}): PlanCoachMessage => ({
  id: 1,
  role: 'user',
  content: 'I want to run a half marathon in 10 weeks',
  created_at: '2026-04-01T10:00:00',
  ...overrides,
})

const PLAN_JSON_CONTENT =
  '```json\n[{"date":"2026-04-07","name":"Easy Run","description":"Recovery","steps_spec":"30m@Z2","sport_type":"running"}]\n```'

const renderChatTab = async () => {
  const { ChatTab } = await import('../components/plan-coach/ChatTab')
  return render(
    <MemoryRouter>
      <ChatTab />
    </MemoryRouter>
  )
}

// ---------------------------------------------------------------------------
// ChatTab
// ---------------------------------------------------------------------------

describe('ChatTab', () => {
  beforeEach(() => {
    mockGetChatHistory.mockReset()
    mockSendChatMessage.mockReset()
    mockValidatePlan.mockReset()
    mockCommitPlan.mockReset()
  })

  it('shows empty state prompt when no messages exist', async () => {
    mockGetChatHistory.mockResolvedValue([])
    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByText(/to get started, share/i)).toBeInTheDocument()
    })
  })

  it('displays loaded chat messages', async () => {
    mockGetChatHistory.mockResolvedValue([
      makeMsg({ id: 1, role: 'user', content: 'Plan me a 5K' }),
      makeMsg({ id: 2, role: 'assistant', content: 'Great! Here is your plan.' }),
    ])
    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByText('Plan me a 5K')).toBeInTheDocument()
      expect(screen.getByText('Great! Here is your plan.')).toBeInTheDocument()
    })
  })

  it('shows error message when history fails to load', async () => {
    mockGetChatHistory.mockRejectedValue(new Error('Network error'))
    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByText(/failed to load chat history/i)).toBeInTheDocument()
    })
  })

  it('send button is disabled when input is empty', async () => {
    mockGetChatHistory.mockResolvedValue([])
    await renderChatTab()
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled()
  })

  it('sends a message and reloads history', async () => {
    const user = userEvent.setup()
    const assistantMsg = makeMsg({ id: 2, role: 'assistant', content: 'Here is your plan!' })
    mockGetChatHistory
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        makeMsg({ id: 1, role: 'user', content: 'Help me train' }),
        assistantMsg,
      ])
    mockSendChatMessage.mockResolvedValue(assistantMsg)

    await renderChatTab()
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByPlaceholderText(/describe your training goal/i), 'Help me train')
    await user.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => {
      expect(mockSendChatMessage).toHaveBeenCalledWith('Help me train')
      expect(screen.getByText('Here is your plan!')).toBeInTheDocument()
    })
  })

  it('shows error when send fails', async () => {
    const user = userEvent.setup()
    mockGetChatHistory.mockResolvedValue([])
    mockSendChatMessage.mockRejectedValue(new Error('Service unavailable'))

    await renderChatTab()
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())

    await user.type(screen.getByPlaceholderText(/describe your training goal/i), 'Hello')
    await user.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => {
      expect(screen.getByText(/service unavailable/i)).toBeInTheDocument()
    })
  })

  it('shows Preview & Validate button when assistant message contains JSON plan', async () => {
    mockGetChatHistory.mockResolvedValue([
      makeMsg({ id: 1, role: 'user', content: 'Give me a plan' }),
      makeMsg({ id: 2, role: 'assistant', content: PLAN_JSON_CONTENT }),
    ])
    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /preview & validate/i })).toBeInTheDocument()
    })
  })

  it('does not show Preview & Validate button for user messages', async () => {
    // User message with JSON block (edge case) — no validate button should appear
    mockGetChatHistory.mockResolvedValue([
      makeMsg({ id: 1, role: 'user', content: PLAN_JSON_CONTENT }),
    ])
    await renderChatTab()
    await waitFor(() => expect(screen.queryByText('Loading…')).not.toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /preview & validate/i })).not.toBeInTheDocument()
  })

  it('clicking Preview & Validate triggers validatePlan and shows ValidationPanel', async () => {
    const user = userEvent.setup()
    mockGetChatHistory.mockResolvedValue([
      makeMsg({ id: 1, role: 'user', content: 'Give me a plan' }),
      makeMsg({ id: 2, role: 'assistant', content: PLAN_JSON_CONTENT }),
    ])
    mockValidatePlan.mockResolvedValue({
      plan_id: 55,
      rows: [{ row: 1, date: '2026-04-07', name: 'Easy Run', steps_spec: '30m@Z2', sport_type: 'running', valid: true, error: null }],
      diff: null,
    } satisfies ValidateResult)

    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /preview & validate/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /preview & validate/i }))

    await waitFor(() => {
      expect(mockValidatePlan).toHaveBeenCalledTimes(1)
      expect(screen.getByText('Easy Run')).toBeInTheDocument()
    })
  })

  it('strips JSON block from displayed assistant message content', async () => {
    mockGetChatHistory.mockResolvedValue([
      makeMsg({ id: 2, role: 'assistant', content: `Here is your plan:\n\n${PLAN_JSON_CONTENT}` }),
    ])
    await renderChatTab()
    await waitFor(() => {
      expect(screen.getByText('Here is your plan:')).toBeInTheDocument()
      // Raw JSON block should not be visible
      expect(screen.queryByText(/```json/)).not.toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// DiffTable smart merge rows
// ---------------------------------------------------------------------------

describe('DiffTable smart merge rows', () => {
  const baseDiff = {
    added: [],
    removed: [],
    changed: [],
    unchanged: [],
    completed_locked: [],
  }

  it('returns null when only unchanged rows (no actionable changes)', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = { ...baseDiff, unchanged: [{ date: '2026-06-01', name: 'Easy Run' }] }
    const { container } = render(<DiffTable diff={diff} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders completed_locked row with lock symbol when other changes exist', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      added: [{ date: '2026-06-02', name: 'Tempo' }],
      completed_locked: [{ date: '2026-06-01', name: 'Easy Run' }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByTestId('diff-table')).toBeInTheDocument()
    expect(screen.getByText('⊘')).toBeInTheDocument()
    expect(screen.getByText(/locked/i)).toBeInTheDocument()
  })

  it('renders changed row with before→after steps_spec', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      changed: [{
        date: '2026-06-01',
        name: 'Easy Run',
        old_name: 'Easy Run',
        old_steps_spec: '30m@Z2',
        new_steps_spec: '40m@Z2',
      }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByText('30m@Z2')).toBeInTheDocument()
    expect(screen.getByText('40m@Z2')).toBeInTheDocument()
  })

  it('header shows unchanged and locked counts when non-zero', async () => {
    const { DiffTable } = await import('../components/plan-coach/DiffTable')
    const diff = {
      ...baseDiff,
      added: [{ date: '2026-06-02', name: 'Tempo' }],
      unchanged: [{ date: '2026-06-03', name: 'Rest' }],
      completed_locked: [{ date: '2026-06-01', name: 'Easy Run' }],
    }
    render(<DiffTable diff={diff} />)
    expect(screen.getByText(/=1\s*unchanged/)).toBeInTheDocument()
    expect(screen.getByText(/⊘1\s*locked/)).toBeInTheDocument()
  })
})

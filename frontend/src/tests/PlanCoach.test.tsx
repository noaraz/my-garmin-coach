import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ValidateResult, ValidateRow } from '../api/types'

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const { mockValidatePlan, mockCommitPlan, mockGetActivePlan, mockNavigate } = vi.hoisted(() => ({
  mockValidatePlan: vi.fn(),
  mockCommitPlan: vi.fn(),
  mockGetActivePlan: vi.fn(),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    validatePlan: mockValidatePlan,
    commitPlan: mockCommitPlan,
    getActivePlan: mockGetActivePlan,
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
// PlanCoachPage — tabs
// ---------------------------------------------------------------------------

describe('PlanCoachPage', () => {
  beforeEach(() => {
    mockGetActivePlan.mockReset()
    mockGetActivePlan.mockResolvedValue(null)
  })

  it('renders Plan tab by default', async () => {
    await renderPage()
    expect(screen.getByRole('tab', { name: /plan/i })).toBeInTheDocument()
    // Chat tab present but disabled
    const chatTab = screen.getByRole('tab', { name: /chat/i })
    expect(chatTab).toBeDisabled()
  })

  it('shows CsvImportTab content on Plan tab', async () => {
    await renderPage()
    // The file input should be visible
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeInTheDocument()
  })
})

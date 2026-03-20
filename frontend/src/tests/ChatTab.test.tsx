import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { PlanCoachMessage, ValidateResult } from '../api/types'
import { ChatTab } from '../components/plan-coach/ChatTab'

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const {
  mockGetChatHistory,
  mockSendChatMessage,
  mockValidatePlan,
  mockCommitPlan,
  mockNavigate,
} = vi.hoisted(() => ({
  mockGetChatHistory: vi.fn(),
  mockSendChatMessage: vi.fn(),
  mockValidatePlan: vi.fn(),
  mockCommitPlan: vi.fn(),
  mockNavigate: vi.fn(),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    getChatHistory: mockGetChatHistory,
    sendChatMessage: mockSendChatMessage,
    validatePlan: mockValidatePlan,
    commitPlan: mockCommitPlan,
  }
})

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeMsg = (id: number, role: 'user' | 'assistant', content: string): PlanCoachMessage => ({
  id,
  role,
  content,
  created_at: '2026-04-01T10:00:00',
})

const JSON_BLOCK = '```json\n[\n  {"date":"2027-04-07","name":"Easy Run","description":"","steps_spec":"10m@Z1","sport_type":"running"}\n]\n```'

const successValidateResult: ValidateResult = {
  plan_id: 99,
  rows: [{
    row: 1,
    date: '2027-04-07',
    name: 'Easy Run',
    steps_spec: '10m@Z1',
    sport_type: 'running',
    valid: true,
    error: null,
  }],
  diff: null,
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

function renderChatTab() {
  return render(
    <MemoryRouter>
      <ChatTab />
    </MemoryRouter>
  )
}

beforeEach(() => {
  mockGetChatHistory.mockReset()
  mockSendChatMessage.mockReset()
  mockValidatePlan.mockReset()
  mockCommitPlan.mockReset()
  mockNavigate.mockReset()
  mockGetChatHistory.mockResolvedValue([])
  mockSendChatMessage.mockResolvedValue(makeMsg(2, 'assistant', 'Here is your plan!'))
  mockValidatePlan.mockResolvedValue(successValidateResult)
  mockCommitPlan.mockResolvedValue({ plan_id: 99, name: 'Chat Plan', workout_count: 1, start_date: '2027-04-07' })
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChatTab', () => {
  describe('initial load', () => {
    it('shows empty state message when no history', async () => {
      renderChatTab()
      await waitFor(() => {
        expect(screen.getByText(/race goal/i)).toBeTruthy()
      })
    })

    it('renders existing messages from history', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'user', 'Build me a 5K plan'),
        makeMsg(2, 'assistant', 'Sure! Here is a plan.'),
      ])
      renderChatTab()
      await waitFor(() => {
        expect(screen.getByText('Build me a 5K plan')).toBeTruthy()
        expect(screen.getByText('Sure! Here is a plan.')).toBeTruthy()
      })
    })
  })

  describe('sending messages', () => {
    it('sends message on button click and reloads history', async () => {
      const user = userEvent.setup()
      mockGetChatHistory
        .mockResolvedValueOnce([])
        .mockResolvedValue([
          makeMsg(1, 'user', 'Hello coach'),
          makeMsg(2, 'assistant', 'Hello! I am ready to help.'),
        ])
      renderChatTab()
      await waitFor(() => screen.getByPlaceholderText(/training goal/i))

      const textarea = screen.getByPlaceholderText(/training goal/i)
      await user.type(textarea, 'Hello coach')
      await user.click(screen.getByText('Send'))

      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalledWith('Hello coach')
      })
      await waitFor(() => {
        expect(screen.getByText('Hello! I am ready to help.')).toBeTruthy()
      })
    })

    it('sends message on Enter key', async () => {
      const user = userEvent.setup()
      mockGetChatHistory.mockResolvedValue([])
      renderChatTab()
      await waitFor(() => screen.getByPlaceholderText(/training goal/i))

      const textarea = screen.getByPlaceholderText(/training goal/i)
      await user.type(textarea, 'My goal')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(mockSendChatMessage).toHaveBeenCalledWith('My goal')
      })
    })

    it('does not send on Shift+Enter', async () => {
      const user = userEvent.setup()
      mockGetChatHistory.mockResolvedValue([])
      renderChatTab()
      await waitFor(() => screen.getByPlaceholderText(/training goal/i))

      const textarea = screen.getByPlaceholderText(/training goal/i)
      await user.type(textarea, 'Line one')
      await user.keyboard('{Shift>}{Enter}{/Shift}')

      expect(mockSendChatMessage).not.toHaveBeenCalled()
    })

    it('Send button is disabled when input is empty', async () => {
      renderChatTab()
      await waitFor(() => screen.getByText('Send'))
      const btn = screen.getByText('Send') as HTMLButtonElement
      expect(btn.disabled).toBe(true)
    })
  })

  describe('plan detection', () => {
    it('shows Validate button when assistant message contains JSON block', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'user', 'Build a plan'),
        makeMsg(2, 'assistant', `Here is your plan:\n${JSON_BLOCK}`),
      ])
      renderChatTab()
      await waitFor(() => {
        expect(screen.getByText(/Preview & Validate/i)).toBeTruthy()
      })
    })

    it('does not show Validate button when assistant message has no JSON block', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'assistant', 'Just a conversational response, no plan yet.'),
      ])
      renderChatTab()
      await waitFor(() => {
        expect(screen.getByText('Just a conversational response, no plan yet.')).toBeTruthy()
      })
      expect(screen.queryByText(/Preview & Validate/i)).toBeNull()
    })

    it('shows ValidationTable after clicking Validate', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'assistant', `Your plan:\n${JSON_BLOCK}`),
      ])
      const user = userEvent.setup()
      renderChatTab()

      await waitFor(() => screen.getByText(/Preview & Validate/i))
      await user.click(screen.getByText(/Preview & Validate/i))

      await waitFor(() => {
        expect(mockValidatePlan).toHaveBeenCalled()
      })
      await waitFor(() => {
        expect(screen.getByText('Easy Run')).toBeTruthy()
      })
    })

    it('shows DiffTable when validate result has a diff', async () => {
      const diffResult: ValidateResult = {
        ...successValidateResult,
        diff: {
          added: [{ date: '2027-04-08', name: 'Tempo Run' }],
          removed: [],
          changed: [],
        },
      }
      mockValidatePlan.mockResolvedValue(diffResult)
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'assistant', `Your plan:\n${JSON_BLOCK}`),
      ])
      const user = userEvent.setup()
      renderChatTab()

      await waitFor(() => screen.getByText(/Preview & Validate/i))
      await user.click(screen.getByText(/Preview & Validate/i))

      await waitFor(() => {
        expect(screen.getByText(/Changes vs current plan/i)).toBeTruthy()
      })
    })

    it('Import button calls commitPlan and navigates on success', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'assistant', `Your plan:\n${JSON_BLOCK}`),
      ])
      const user = userEvent.setup()
      renderChatTab()

      await waitFor(() => screen.getByText(/Preview & Validate/i))
      await user.click(screen.getByText(/Preview & Validate/i))
      await waitFor(() => screen.getByText(/Import to Calendar/i))
      await user.click(screen.getByText(/Import to Calendar/i))

      await waitFor(() => {
        expect(mockCommitPlan).toHaveBeenCalledWith(99)
        expect(mockNavigate).toHaveBeenCalledWith('/calendar?date=2027-04-07')
      })
    })

    it('Back to chat button dismisses the validation panel', async () => {
      mockGetChatHistory.mockResolvedValue([
        makeMsg(1, 'assistant', `Your plan:\n${JSON_BLOCK}`),
      ])
      const user = userEvent.setup()
      renderChatTab()

      await waitFor(() => screen.getByText(/Preview & Validate/i))
      await user.click(screen.getByText(/Preview & Validate/i))
      await waitFor(() => screen.getByText(/Back to chat/i))
      await user.click(screen.getByText(/Back to chat/i))

      await waitFor(() => {
        expect(screen.queryByText(/Back to chat/i)).toBeNull()
      })
    })
  })
})

/// <reference types="vitest" />
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DiffTable } from './DiffTable'
import type { DiffResult } from '../../api/types'

const emptyDiff: DiffResult = {
  added: [],
  removed: [],
  changed: [],
  unchanged: [],
  completed_locked: [],
  past_locked: [],
}

describe('DiffTable', () => {
  it('renders past_locked rows with ↩ symbol', () => {
    const diff: DiffResult = {
      ...emptyDiff,
      past_locked: [{ date: '2020-01-01', name: 'Old Run' }],
    }
    render(<DiffTable diff={diff} />)

    expect(screen.getByText('↩')).toBeInTheDocument()
    expect(screen.getByText('Old Run')).toBeInTheDocument()
    expect(screen.getByText('(kept)')).toBeInTheDocument()
  })

  it('shows ↩N past (kept) in summary header', () => {
    const diff: DiffResult = {
      ...emptyDiff,
      past_locked: [
        { date: '2020-01-01', name: 'Old Run' },
        { date: '2020-01-03', name: 'Easy Run' },
      ],
    }
    render(<DiffTable diff={diff} />)

    expect(screen.getByText('↩2 past (kept)')).toBeInTheDocument()
  })

  it('does not count past_locked in removed count', () => {
    const diff: DiffResult = {
      ...emptyDiff,
      removed: [{ date: '2099-12-31', name: 'Future Run' }],
      past_locked: [{ date: '2020-01-01', name: 'Old Run' }],
    }
    render(<DiffTable diff={diff} />)

    expect(screen.getByText('−1 removed')).toBeInTheDocument()
    expect(screen.getByText('↩1 past (kept)')).toBeInTheDocument()
  })

  it('renders the table when only past_locked rows exist', () => {
    const diff: DiffResult = {
      ...emptyDiff,
      past_locked: [{ date: '2020-01-01', name: 'Old Run' }],
    }
    render(<DiffTable diff={diff} />)

    expect(screen.getByTestId('diff-table')).toBeInTheDocument()
  })

  it('returns null when no actionable or past_locked rows', () => {
    render(<DiffTable diff={emptyDiff} />)

    expect(screen.queryByTestId('diff-table')).not.toBeInTheDocument()
  })
})

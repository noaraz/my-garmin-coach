import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import ExportModal from '../components/ExportModal'

const { mockExportActivities } = vi.hoisted(() => ({
  mockExportActivities: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, exportActivities: mockExportActivities }
})

describe('ExportModal', () => {
  beforeEach(() => {
    mockExportActivities.mockReset()
    mockExportActivities.mockResolvedValue(undefined)
  })

  it('renders when open', () => {
    render(<ExportModal isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText(/export activity data/i)).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(<ExportModal isOpen={false} onClose={vi.fn()} />)
    expect(screen.queryByText(/export activity data/i)).not.toBeInTheDocument()
  })

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn()
    render(<ExportModal isOpen={true} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls exportActivities with selected range on submit', async () => {
    render(<ExportModal isOpen={true} onClose={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /download/i }))
    await waitFor(() => expect(mockExportActivities).toHaveBeenCalled())
  })

  it('shows loading state while downloading', async () => {
    mockExportActivities.mockImplementation(() => new Promise(() => {})) // never resolves
    render(<ExportModal isOpen={true} onClose={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /download/i }))
    await waitFor(() => expect(screen.getByText(/fetching/i)).toBeInTheDocument())
  })

  it('shows error message on failure', async () => {
    mockExportActivities.mockRejectedValue(new Error('Export failed'))
    render(<ExportModal isOpen={true} onClose={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /download/i }))
    await waitFor(() => expect(screen.getByText(/failed/i)).toBeInTheDocument())
  })
})

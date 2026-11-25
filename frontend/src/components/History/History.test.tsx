import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Transcription } from '../../api/types'
import History from './History'

const make = (n: number, text = `entry ${n}`): Transcription => ({
  id: String(n),
  text,
  languages: ['hi', 'en'],
  engine: 'gemini-3.5-transcribe-live',
  source: 'spoken',
  status: 'complete',
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-01T10:00:00Z',
})

const base = {
  items: [] as Transcription[],
  loading: false,
  loadingMore: false,
  error: null as string | null,
  hasMore: false,
  filtered: false,
  onOpen: vi.fn(),
  onLoadMore: vi.fn(),
  onRetry: vi.fn(),
  onAdd: vi.fn(),
  onClearFilters: vi.fn(),
}

describe('History', () => {
  it('shows a loading state', () => {
    render(<History {...base} loading />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows a friendly empty state', () => {
    render(<History {...base} />)
    expect(screen.getByText(/record your first/i)).toBeInTheDocument()
  })

  it('shows an error with retry', async () => {
    const onRetry = vi.fn()
    render(<History {...base} error="Cannot reach the server." onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/cannot reach/i)
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalled()
  })

  it('lists entries with preview, language chips and opens one', async () => {
    const onOpen = vi.fn()
    const items = [make(1, 'कल meeting है at 10 AM'), make(2)]
    render(<History {...base} items={items} onOpen={onOpen} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getAllByText('hi').length).toBeGreaterThan(0)
    await userEvent.click(screen.getByRole('button', { name: /कल meeting/ }))
    expect(onOpen).toHaveBeenCalledWith(items[0])
  })

  it('marks interrupted entries', () => {
    render(<History {...base} items={[{ ...make(1), status: 'interrupted' }]} />)
    expect(screen.getByText(/interrupted/i)).toBeInTheDocument()
  })

  it('Load more appears only when there are more pages', async () => {
    const onLoadMore = vi.fn()
    const { rerender } = render(<History {...base} items={[make(1)]} onLoadMore={onLoadMore} />)
    expect(screen.queryByRole('button', { name: /load more/i })).toBeNull()
    rerender(<History {...base} items={[make(1)]} hasMore onLoadMore={onLoadMore} />)
    await userEvent.click(screen.getByRole('button', { name: /load more/i }))
    expect(onLoadMore).toHaveBeenCalled()
  })

  it('has an Add entry button', async () => {
    const onAdd = vi.fn()
    render(<History {...base} onAdd={onAdd} />)
    await userEvent.click(screen.getByRole('button', { name: /add entry/i }))
    expect(onAdd).toHaveBeenCalled()
  })
})

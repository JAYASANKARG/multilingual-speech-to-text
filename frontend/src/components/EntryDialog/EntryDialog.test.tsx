import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Transcription } from '../../api/types'
import EntryDialog from './EntryDialog'

const entry: Transcription = {
  id: '1',
  text: 'कल meeting है',
  languages: ['hi', 'en'],
  engine: 'gemini-3.5-transcribe-live',
  source: 'spoken',
  status: 'complete',
  created_at: '2026-01-01T10:00:00Z',
  updated_at: '2026-01-02T11:00:00Z',
}

const setup = (overrides = {}) => {
  const props = {
    entry,
    onSave: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn().mockResolvedValue(undefined),
    onClose: vi.fn(),
    ...overrides,
  }
  render(<EntryDialog {...props} />)
  return props
}

describe('EntryDialog', () => {
  it('shows full text, both timestamps, languages and engine', () => {
    setup()
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('कल meeting है')
    expect(dialog).toHaveTextContent(/created/i)
    expect(dialog).toHaveTextContent(/last modified/i)
    expect(dialog).toHaveTextContent('hi')
    expect(dialog).toHaveTextContent('gemini-3.5-transcribe-live')
  })

  it('edits and saves text', async () => {
    const { onSave } = setup()
    await userEvent.click(screen.getByRole('button', { name: /edit/i }))
    const box = screen.getByRole('textbox')
    await userEvent.clear(box)
    await userEvent.type(box, 'fixed text')
    await userEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(onSave).toHaveBeenCalledWith('fixed text')
  })

  it('blocks blank text with a reason', async () => {
    const { onSave } = setup()
    await userEvent.click(screen.getByRole('button', { name: /edit/i }))
    await userEvent.clear(screen.getByRole('textbox'))
    await userEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(screen.getByRole('alert')).toHaveTextContent(/text cannot be empty/i)
    expect(onSave).not.toHaveBeenCalled()
  })

  it('shows server errors from save', async () => {
    setup({ onSave: vi.fn().mockRejectedValue(new Error('Server said no')) })
    await userEvent.click(screen.getByRole('button', { name: /edit/i }))
    await userEvent.type(screen.getByRole('textbox'), '!')
    await userEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/server said no/i)
  })

  it('delete asks for confirmation; cancel leaves the entry intact', async () => {
    const { onDelete } = setup()
    await userEvent.click(screen.getByRole('button', { name: /^delete/i }))
    const confirm = screen.getByRole('alertdialog')
    expect(confirm).toHaveTextContent(/permanently/i)
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('confirming delete removes the entry', async () => {
    const { onDelete, onClose } = setup()
    await userEvent.click(screen.getByRole('button', { name: /^delete/i }))
    await userEvent.click(screen.getByRole('button', { name: /delete permanently/i }))
    expect(onDelete).toHaveBeenCalled()
    await vi.waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('Escape closes the confirm dialog first', async () => {
    const { onClose } = setup()
    await userEvent.click(screen.getByRole('button', { name: /^delete/i }))
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('manual-add mode starts empty and saves new text', async () => {
    const { onSave } = setup({ entry: null, onDelete: undefined })
    expect(screen.getByRole('heading', { name: /add entry/i })).toBeInTheDocument()
    await userEvent.type(screen.getByRole('textbox'), 'typed by hand')
    await userEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(onSave).toHaveBeenCalledWith('typed by hand')
    expect(screen.queryByRole('button', { name: /^delete/i })).toBeNull()
  })
})

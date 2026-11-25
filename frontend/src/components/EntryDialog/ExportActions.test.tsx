import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ExportActions from './ExportActions'

afterEach(() => vi.restoreAllMocks())

describe('ExportActions', () => {
  it('Copy writes the full text to the clipboard and confirms', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    render(<ExportActions text="कल meeting है" createdAt="2026-01-02T03:04:05Z" />)
    await userEvent.click(screen.getByRole('button', { name: /copy/i }))
    expect(writeText).toHaveBeenCalledWith('कल meeting है')
    expect(await screen.findByText(/copied/i)).toBeInTheDocument()
    vi.unstubAllGlobals()
  })

  it('Copy tells the user when the clipboard is unavailable', async () => {
    vi.stubGlobal('navigator', { ...navigator, clipboard: undefined })
    render(<ExportActions text="x" createdAt="2026-01-02T03:04:05Z" />)
    await userEvent.click(screen.getByRole('button', { name: /copy/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/select the text/i)
    vi.unstubAllGlobals()
  })

  it('Download creates a UTF-8 text file named from the creation time', async () => {
    const created: Blob[] = []
    const createObjectURL = vi.fn((b: Blob) => {
      created.push(b)
      return 'blob:x'
    })
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    render(<ExportActions text="कल meeting है" createdAt="2026-01-02T03:04:05Z" />)
    await userEvent.click(screen.getByRole('button', { name: /download/i }))
    expect(click).toHaveBeenCalled()
    expect(created[0].type).toBe('text/plain;charset=utf-8')
    expect(await created[0].text()).toBe('कल meeting है')
  })
})

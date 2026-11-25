import { renderHook, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Language } from '../../api/types'
import { useLanguages } from '../../hooks/useLanguages'
import LanguagePicker from './LanguagePicker'

const languages: Language[] = [
  { code: 'auto', name: 'Auto-detect (Hindi + English)', pinnable: true },
  { code: 'hi', name: 'Hindi', pinnable: true },
  { code: 'mr', name: 'Marathi', pinnable: true },
  { code: 'ta', name: 'Tamil', pinnable: false },
]

afterEach(() => vi.restoreAllMocks())

describe('LanguagePicker', () => {
  it('defaults to auto-detect and lists every language', () => {
    render(<LanguagePicker languages={languages} value="auto" onChange={() => {}} />)
    expect(screen.getByRole('combobox')).toHaveValue('auto')
    expect(screen.getAllByRole('option')).toHaveLength(4)
  })

  it('does not allow pinning non-pinnable languages', () => {
    render(<LanguagePicker languages={languages} value="auto" onChange={() => {}} />)
    expect(screen.getByRole('option', { name: /tamil/i })).toBeDisabled()
  })

  it('reports selection', async () => {
    const onChange = vi.fn()
    render(<LanguagePicker languages={languages} value="auto" onChange={onChange} />)
    await userEvent.selectOptions(screen.getByRole('combobox'), 'mr')
    expect(onChange).toHaveBeenCalledWith('mr')
  })

  it('is disabled while a session runs', () => {
    render(<LanguagePicker languages={languages} value="auto" onChange={() => {}} disabled />)
    expect(screen.getByRole('combobox')).toBeDisabled()
  })
})

describe('useLanguages', () => {
  it('loads options from /api/languages', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(languages)))
    const { result } = renderHook(() => useLanguages())
    await waitFor(() => expect(result.current).toHaveLength(4))
    expect(fetch).toHaveBeenCalledWith('/api/languages', expect.anything())
  })

  it('falls back to auto-detect only when the request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    const { result } = renderHook(() => useLanguages())
    expect(result.current[0].code).toBe('auto')
  })
})

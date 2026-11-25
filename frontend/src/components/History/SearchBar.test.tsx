import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Language } from '../../api/types'
import SearchBar from './SearchBar'

const languages: Language[] = [
  { code: 'auto', name: 'Auto-detect', pinnable: true },
  { code: 'hi', name: 'Hindi', pinnable: true },
  { code: 'ta', name: 'Tamil', pinnable: false },
]

describe('SearchBar', () => {
  it('debounces typing before calling onQueryChange', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onQueryChange = vi.fn()
    render(
      <SearchBar
        languages={languages}
        q=""
        language=""
        onQueryChange={onQueryChange}
        onLanguageChange={() => {}}
        onClear={() => {}}
      />,
    )
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    await user.type(screen.getByRole('searchbox'), 'meet')
    expect(onQueryChange).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(350)
    expect(onQueryChange).toHaveBeenCalledTimes(1)
    expect(onQueryChange).toHaveBeenCalledWith('meet')
    vi.useRealTimers()
  })

  it('language filter lists real languages (not auto) and reports changes', async () => {
    const onLanguageChange = vi.fn()
    render(
      <SearchBar
        languages={languages}
        q=""
        language=""
        onQueryChange={() => {}}
        onLanguageChange={onLanguageChange}
        onClear={() => {}}
      />,
    )
    const select = screen.getByRole('combobox', { name: /filter by language/i })
    expect(screen.getByRole('option', { name: /all languages/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /auto/i })).toBeNull()
    await userEvent.selectOptions(select, 'hi')
    expect(onLanguageChange).toHaveBeenCalledWith('hi')
  })

  it('Clear resets filters and is shown only when a filter is active', async () => {
    const onClear = vi.fn()
    const { rerender } = render(
      <SearchBar languages={languages} q="" language="" onQueryChange={() => {}} onLanguageChange={() => {}} onClear={onClear} />,
    )
    expect(screen.queryByRole('button', { name: /clear/i })).toBeNull()
    rerender(
      <SearchBar languages={languages} q="x" language="" onQueryChange={() => {}} onLanguageChange={() => {}} onClear={onClear} />,
    )
    await userEvent.click(screen.getByRole('button', { name: /clear/i }))
    expect(onClear).toHaveBeenCalled()
  })
})

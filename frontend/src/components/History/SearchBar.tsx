import { useEffect, useRef, useState } from 'react'
import type { Language } from '../../api/types'

interface Props {
  languages: Language[]
  q: string
  language: string
  onQueryChange: (q: string) => void
  onLanguageChange: (code: string) => void
  onClear: () => void
}

const DEBOUNCE_MS = 300

export default function SearchBar({ languages, q, language, onQueryChange, onLanguageChange, onClear }: Props) {
  const [draft, setDraft] = useState(q)
  const [prevQ, setPrevQ] = useState(q)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Keep the box in step when the query is cleared from outside.
  if (q !== prevQ) {
    setPrevQ(q)
    setDraft(q)
  }

  useEffect(() => () => clearTimeout(timer.current), [])

  const onInput = (value: string) => {
    setDraft(value)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => onQueryChange(value.trim()), DEBOUNCE_MS)
  }

  const active = q !== '' || language !== ''

  return (
    <div className="search-bar">
      <input
        type="search"
        aria-label="Search transcriptions"
        placeholder="Search text…"
        value={draft}
        onChange={(e) => onInput(e.target.value)}
        maxLength={200}
      />
      <select
        aria-label="Filter by language"
        value={language}
        onChange={(e) => onLanguageChange(e.target.value)}
      >
        <option value="">All languages</option>
        {languages
          .filter((l) => l.code !== 'auto')
          .map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
      </select>
      {active && <button onClick={onClear}>Clear</button>}
    </div>
  )
}

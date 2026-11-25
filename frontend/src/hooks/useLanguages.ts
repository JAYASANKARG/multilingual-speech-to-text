import { useEffect, useState } from 'react'
import { request } from '../api/client'
import type { Language } from '../api/types'

const FALLBACK: Language[] = [{ code: 'auto', name: 'Auto-detect (Hindi + English)', pinnable: true }]

export function useLanguages(): Language[] {
  const [languages, setLanguages] = useState<Language[]>(FALLBACK)
  useEffect(() => {
    let cancelled = false
    request<Language[]>('/api/languages')
      .then((list) => {
        if (!cancelled && list.length > 0) setLanguages(list)
      })
      .catch(() => {
        // keep the auto-detect fallback: the recorder still works
      })
    return () => {
      cancelled = true
    }
  }, [])
  return languages
}

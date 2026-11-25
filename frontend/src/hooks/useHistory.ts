import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ApiError,
  createTranscription,
  deleteTranscription,
  listTranscriptions,
  updateTranscription,
} from '../api/client'
import type { Transcription } from '../api/types'

const PAGE_SIZE = 20

function messageOf(err: unknown): string {
  return err instanceof ApiError || err instanceof Error ? err.message : 'Something went wrong.'
}

export function useHistory() {
  const [items, setItems] = useState<Transcription[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [language, setLanguage] = useState('')
  const requestId = useRef(0)

  const load = useCallback(async (id: number) => {
    try {
      const page = await listTranscriptions({ limit: PAGE_SIZE, q, language })
      if (id !== requestId.current) return
      setItems(page.items)
      setNextCursor(page.next_cursor)
    } catch (err) {
      if (id === requestId.current) setError(messageOf(err))
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [q, language])

  const refresh = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    await load(id)
  }, [load])

  const loadMore = useCallback(async () => {
    if (!nextCursor) return
    const id = requestId.current
    setLoadingMore(true)
    try {
      const page = await listTranscriptions({ limit: PAGE_SIZE, cursor: nextCursor, q, language })
      if (id !== requestId.current) return
      setItems((prev) => {
        const seen = new Set(prev.map((p) => p.id))
        return [...prev, ...page.items.filter((p) => !seen.has(p.id))]
      })
      setNextCursor(page.next_cursor)
    } catch (err) {
      if (id === requestId.current) setError(messageOf(err))
    } finally {
      setLoadingMore(false)
    }
  }, [nextCursor, q, language])

  const add = useCallback(
    async (text: string) => {
      await createTranscription(text)
      await refresh()
    },
    [refresh],
  )

  const update = useCallback(async (id: string, text: string) => {
    const updated = await updateTranscription(id, text)
    setItems((prev) => prev.map((p) => (p.id === id ? updated : p)))
    return updated
  }, [])

  const remove = useCallback(async (id: string) => {
    try {
      await deleteTranscription(id)
    } catch (err) {
      // already gone elsewhere: treat as deleted
      if (!(err instanceof ApiError && err.status === 404)) throw err
    }
    setItems((prev) => prev.filter((p) => p.id !== id))
  }, [])

  const applyFilters = useCallback((nextQ: string, nextLanguage: string) => {
    setLoading(true)
    setError(null)
    setItems([])
    setNextCursor(null)
    setQ(nextQ)
    setLanguage(nextLanguage)
  }, [])

  useEffect(() => {
    void load(++requestId.current)
  }, [load])

  return {
    items,
    loading,
    loadingMore,
    error,
    hasMore: nextCursor !== null,
    q,
    language,
    filtered: q !== '' || language !== '',
    setQuery: (value: string) => applyFilters(value, language),
    setLanguage: (value: string) => applyFilters(q, value),
    clearFilters: () => applyFilters('', ''),
    refresh,
    loadMore,
    add,
    update,
    remove,
  }
}

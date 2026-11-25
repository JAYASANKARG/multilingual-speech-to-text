import { useCallback, useEffect, useState } from 'react'
import { request } from '../api/client'
import type { Quota } from '../api/types'

// Unknown quota must never block recording: the server enforces the limit anyway.
const fetchQuota = () => request<Quota>('/api/quota').catch(() => null)

export function useQuota() {
  const [quota, setQuota] = useState<Quota | null>(null)

  const refresh = useCallback(async () => {
    setQuota(await fetchQuota())
  }, [])

  useEffect(() => {
    let cancelled = false
    void fetchQuota().then((q) => {
      if (!cancelled) setQuota(q)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { quota, refresh }
}

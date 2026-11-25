import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useQuota } from './useQuota'

afterEach(() => vi.restoreAllMocks())

describe('useQuota', () => {
  it('loads the quota', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ limit: 10, remaining: 7, resets_at: null })),
    )
    const { result } = renderHook(() => useQuota())
    await waitFor(() => expect(result.current.quota?.remaining).toBe(7))
  })

  it('stays null when the request fails (recording is still attempted)', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    const { result } = renderHook(() => useQuota())
    await new Promise((r) => setTimeout(r, 20))
    expect(result.current.quota).toBeNull()
  })
})

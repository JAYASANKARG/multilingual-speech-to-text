import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request, wsUrl } from './client'

afterEach(() => vi.restoreAllMocks())

function mockFetch(status: number, body: unknown) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  )
}

describe('request', () => {
  it('returns parsed JSON on success', async () => {
    mockFetch(200, { status: 'ok' })
    await expect(request('/api/health')).resolves.toEqual({ status: 'ok' })
  })

  it('maps 404 detail to ApiError', async () => {
    mockFetch(404, { detail: 'Not found' })
    await expect(request('/api/x')).rejects.toMatchObject({ status: 404, detail: 'Not found' })
  })

  it('extracts the message of a 422 validation error', async () => {
    mockFetch(422, { detail: [{ msg: 'Value error, Text cannot be empty' }] })
    const err = await request('/api/x').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).detail).toBe('Text cannot be empty')
  })

  it('returns undefined for 204', async () => {
    mockFetch(204, undefined)
    await expect(request('/api/x', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('reports network failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('fail'))
    await expect(request('/api/x')).rejects.toMatchObject({ status: 0 })
  })
})

describe('wsUrl', () => {
  it('uses ws for http origins', () => {
    expect(wsUrl('/api/ws/transcribe?language=auto')).toBe(
      `ws://${window.location.host}/api/ws/transcribe?language=auto`,
    )
  })
})

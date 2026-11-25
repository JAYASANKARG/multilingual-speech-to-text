import type { Transcription, TranscriptionPage } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (first?.msg) return first.msg.replace(/^Value error, /, '')
    }
  }
  return fallback
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body !== undefined) headers.set('Content-Type', 'application/json')
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'same-origin' })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check your connection and try again.')
  }
  if (res.status === 204) return undefined as T
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) throw new ApiError(res.status, detailOf(body, `Request failed (${res.status})`))
  return body as T
}

export interface ListParams {
  cursor?: string | null
  limit?: number
  q?: string
  language?: string
}

export function listTranscriptions(params: ListParams = {}): Promise<TranscriptionPage> {
  const query = new URLSearchParams()
  if (params.cursor) query.set('cursor', params.cursor)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.q) query.set('q', params.q)
  if (params.language) query.set('language', params.language)
  const qs = query.toString()
  return request<TranscriptionPage>(`/api/transcriptions${qs ? `?${qs}` : ''}`)
}

export const createTranscription = (text: string) =>
  request<Transcription>('/api/transcriptions', { method: 'POST', body: JSON.stringify({ text }) })

export const updateTranscription = (id: string, text: string) =>
  request<Transcription>(`/api/transcriptions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ text }),
  })

export const deleteTranscription = (id: string) =>
  request<void>(`/api/transcriptions/${id}`, { method: 'DELETE' })

export function wsUrl(path: string): string {
  const base = API_BASE
    ? new URL(API_BASE, window.location.href)
    : new URL(window.location.href)
  const proto = base.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${base.host}${path}`
}

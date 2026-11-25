export type Source = 'spoken' | 'manual'
export type Status = 'complete' | 'interrupted'

export interface Transcription {
  id: string
  text: string
  languages: string[]
  engine: string | null
  source: Source
  status: Status
  created_at: string
  updated_at: string
}

export interface TranscriptionPage {
  items: Transcription[]
  next_cursor: string | null
}

export interface Language {
  code: string
  name: string
  pinnable: boolean
}

export interface Quota {
  limit: number
  remaining: number
  resets_at: string | null
}

export type SessionState = 'connecting' | 'listening' | 'processing'

export type EndReason =
  | 'user_stop'
  | 'silence_timeout'
  | 'max_duration'
  | 'upstream_error'
  | 'client_disconnect'

export type ErrorCode =
  | 'rate_limited'
  | 'capacity'
  | 'upstream_unavailable'
  | 'bad_message'
  | 'internal'

export type ServerMessage =
  | { type: 'state'; state: SessionState }
  | { type: 'interim'; text: string }
  | { type: 'final'; text: string; index: number }
  | {
      type: 'ended'
      reason: EndReason
      transcription: Transcription | null
      unsaved_text?: string
    }
  | { type: 'error'; code: ErrorCode; message: string; retry_at?: string }

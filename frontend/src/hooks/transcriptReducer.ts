import type { EndReason, ErrorCode, ServerMessage, Transcription } from '../api/types'

export type UiState = 'idle' | 'connecting' | 'listening' | 'processing' | 'ended' | 'error'

export type Outcome =
  | { kind: 'saved'; reason: EndReason; transcription: Transcription }
  | { kind: 'nothing'; reason: EndReason }
  | { kind: 'unsaved'; reason: EndReason; text: string }

export type LocalErrorCode = 'mic_denied' | 'mic_unavailable' | 'unsupported' | 'connection_lost'

export interface SessionError {
  code: ErrorCode | LocalErrorCode
  message: string
  retry_at?: string
}

export interface TranscriptState {
  state: UiState
  segments: string[]
  inProgress: string
  outcome: Outcome | null
  error: SessionError | null
}

export type Action =
  | { type: 'start' }
  | { type: 'reset' }
  | { type: 'server'; msg: ServerMessage }
  | { type: 'socket_closed' }
  | { type: 'local_error'; error: SessionError }

export const initialState: TranscriptState = {
  state: 'idle',
  segments: [],
  inProgress: '',
  outcome: null,
  error: null,
}

const TERMINAL_ERRORS: ErrorCode[] = ['rate_limited', 'capacity', 'upstream_unavailable']

export function reducer(state: TranscriptState, action: Action): TranscriptState {
  switch (action.type) {
    case 'start':
      return { ...initialState, state: 'connecting' }
    case 'reset':
      return initialState
    case 'local_error':
      return { ...state, state: 'error', error: action.error }
    case 'socket_closed':
      if (state.state === 'ended' || state.state === 'error' || state.state === 'idle') return state
      return {
        ...state,
        state: 'error',
        error: {
          code: 'connection_lost',
          message: 'The connection was lost. The text below is still shown.',
        },
      }
    case 'server':
      return applyServer(state, action.msg)
  }
}

function applyServer(state: TranscriptState, msg: ServerMessage): TranscriptState {
  switch (msg.type) {
    case 'state':
      return { ...state, state: msg.state }
    case 'interim':
      return { ...state, inProgress: msg.text }
    case 'final': {
      const segments = [...state.segments]
      segments[msg.index] = msg.text
      return { ...state, segments, inProgress: '' }
    }
    case 'ended': {
      let outcome: Outcome
      if (msg.unsaved_text) outcome = { kind: 'unsaved', reason: msg.reason, text: msg.unsaved_text }
      else if (msg.transcription)
        outcome = { kind: 'saved', reason: msg.reason, transcription: msg.transcription }
      else outcome = { kind: 'nothing', reason: msg.reason }
      return { ...state, state: 'ended', inProgress: '', outcome }
    }
    case 'error': {
      if (msg.code === 'bad_message') return state
      const error: SessionError = { code: msg.code, message: msg.message, retry_at: msg.retry_at }
      if (TERMINAL_ERRORS.includes(msg.code)) return { ...state, state: 'error', error }
      return { ...state, error }
    }
  }
}

export function displayText(state: Pick<TranscriptState, 'segments' | 'inProgress'>): string {
  return [...state.segments.filter(Boolean), state.inProgress].filter(Boolean).join(' ').trim()
}

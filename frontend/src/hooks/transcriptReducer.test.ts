import { describe, expect, it } from 'vitest'
import type { Transcription } from '../api/types'
import { displayText, initialState, reducer } from './transcriptReducer'

const entry: Transcription = {
  id: '1',
  text: 'hello',
  languages: ['en'],
  engine: 'm',
  source: 'spoken',
  status: 'complete',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const live = reducer(initialState, { type: 'start' })

describe('transcript reducer', () => {
  it('interim replaces the in-progress text', () => {
    let s = reducer(live, { type: 'server', msg: { type: 'interim', text: 'kal' } })
    s = reducer(s, { type: 'server', msg: { type: 'interim', text: 'kal meeting' } })
    expect(s.inProgress).toBe('kal meeting')
  })

  it('final appends a segment and clears interim', () => {
    let s = reducer(live, { type: 'server', msg: { type: 'interim', text: 'kal' } })
    s = reducer(s, { type: 'server', msg: { type: 'final', text: 'कल meeting', index: 0 } })
    s = reducer(s, { type: 'server', msg: { type: 'interim', text: 'please' } })
    expect(s.segments).toEqual(['कल meeting'])
    expect(displayText(s)).toBe('कल meeting please')
  })

  it('duplicate or out-of-order index replaces the segment', () => {
    let s = reducer(live, { type: 'server', msg: { type: 'final', text: 'b', index: 1 } })
    s = reducer(s, { type: 'server', msg: { type: 'final', text: 'a', index: 0 } })
    s = reducer(s, { type: 'server', msg: { type: 'final', text: 'a2', index: 0 } })
    expect(displayText(s)).toBe('a2 b')
  })

  it('state messages drive the badge state', () => {
    const s = reducer(live, { type: 'server', msg: { type: 'state', state: 'listening' } })
    expect(s.state).toBe('listening')
  })

  it('ended with a transcription is saved', () => {
    const s = reducer(live, {
      type: 'server',
      msg: { type: 'ended', reason: 'user_stop', transcription: entry },
    })
    expect(s.state).toBe('ended')
    expect(s.outcome).toEqual({ kind: 'saved', reason: 'user_stop', transcription: entry })
  })

  it('ended with null means nothing was captured', () => {
    const s = reducer(live, {
      type: 'server',
      msg: { type: 'ended', reason: 'silence_timeout', transcription: null },
    })
    expect(s.outcome).toEqual({ kind: 'nothing', reason: 'silence_timeout' })
  })

  it('ended with unsaved_text keeps the text', () => {
    const s = reducer(live, {
      type: 'server',
      msg: { type: 'ended', reason: 'user_stop', transcription: null, unsaved_text: 'keep' },
    })
    expect(s.outcome).toEqual({ kind: 'unsaved', reason: 'user_stop', text: 'keep' })
  })

  it('terminal errors put the session in error state', () => {
    const s = reducer(live, {
      type: 'server',
      msg: { type: 'error', code: 'rate_limited', message: 'Slow down', retry_at: '2026-01-01T01:00:00Z' },
    })
    expect(s.state).toBe('error')
    expect(s.error).toMatchObject({ code: 'rate_limited', retry_at: '2026-01-01T01:00:00Z' })
  })

  it('bad_message errors are ignored', () => {
    const s = reducer(live, {
      type: 'server',
      msg: { type: 'error', code: 'bad_message', message: 'x' },
    })
    expect(s.state).toBe('connecting')
    expect(s.error).toBeNull()
  })

  it('socket closing mid-session keeps the text and reports connection lost', () => {
    let s = reducer(live, { type: 'server', msg: { type: 'final', text: 'hello', index: 0 } })
    s = reducer(s, { type: 'server', msg: { type: 'state', state: 'listening' } })
    s = reducer(s, { type: 'socket_closed' })
    expect(s.state).toBe('error')
    expect(s.error?.code).toBe('connection_lost')
    expect(displayText(s)).toBe('hello')
  })

  it('socket closing after ended changes nothing', () => {
    let s = reducer(live, {
      type: 'server',
      msg: { type: 'ended', reason: 'user_stop', transcription: entry },
    })
    s = reducer(s, { type: 'socket_closed' })
    expect(s.state).toBe('ended')
  })
})

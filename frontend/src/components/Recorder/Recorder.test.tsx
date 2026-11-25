import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { initialState, type TranscriptState } from '../../hooks/transcriptReducer'
import Recorder from './Recorder'

const start = vi.fn()
const stop = vi.fn()
const reset = vi.fn()
let current: TranscriptState & { slowConnect: boolean }
let quotaValue: { limit: number; remaining: number; resets_at: string | null } | null = null
const refreshQuota = vi.fn()

vi.mock('../../hooks/useQuota', () => ({
  useQuota: () => ({ quota: quotaValue, refresh: refreshQuota }),
}))

vi.mock('../../hooks/useLanguages', () => ({
  useLanguages: () => [
    { code: 'auto', name: 'Auto-detect (Hindi + English)', pinnable: true },
    { code: 'mr', name: 'Marathi', pinnable: true },
  ],
}))

vi.mock('../../hooks/useTranscriber', () => ({
  useTranscriber: () => ({ ...current, start, stop, reset }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.setItem('stt-consent', '1')
  current = { ...initialState, slowConnect: false }
  quotaValue = null
})

describe('Recorder', () => {
  it('idle shows an enabled Start that starts a session', async () => {
    render(<Recorder />)
    const button = screen.getByRole('button', { name: /start/i })
    expect(button).toBeEnabled()
    await userEvent.click(button)
    expect(start).toHaveBeenCalledWith('auto')
  })

  it('starts with the pinned language', async () => {
    render(<Recorder />)
    await userEvent.selectOptions(screen.getByRole('combobox'), 'mr')
    await userEvent.click(screen.getByRole('button', { name: /start/i }))
    expect(start).toHaveBeenCalledWith('mr')
  })

  it('disables the picker during a session', () => {
    current = { ...current, state: 'listening' }
    render(<Recorder />)
    expect(screen.getByRole('combobox')).toBeDisabled()
  })

  it('explains an unavailable service and invites a retry', () => {
    current = {
      ...current,
      state: 'error',
      error: {
        code: 'upstream_unavailable',
        message: 'The speech service is busy or over its free limit right now. Please try again later.',
      },
    }
    render(<Recorder />)
    expect(screen.getByRole('alert')).toHaveTextContent(/try again later/i)
    expect(screen.getByRole('button', { name: /start again/i })).toBeEnabled()
  })

  it('shows the privacy notice before the first recording', async () => {
    localStorage.clear()
    render(<Recorder />)
    await userEvent.click(screen.getByRole('button', { name: /start/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(start).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /i understand/i }))
    expect(start).toHaveBeenCalled()
  })

  it('listening shows Stop, a state badge, and distinct interim text', async () => {
    current = { ...current, state: 'listening', segments: ['कल meeting'], inProgress: 'please' }
    render(<Recorder />)
    expect(screen.getByText(/listening/i)).toBeInTheDocument()
    expect(screen.getByText('कल meeting')).toBeInTheDocument()
    const interim = screen.getByText('please')
    expect(interim).toHaveClass('interim')
    await userEvent.click(screen.getByRole('button', { name: /stop/i }))
    expect(stop).toHaveBeenCalled()
  })

  it('mic denied shows re-enable instructions', () => {
    current = {
      ...current,
      state: 'error',
      error: { code: 'mic_denied', message: 'Microphone access was blocked.' },
    }
    render(<Recorder />)
    expect(screen.getByRole('alert')).toHaveTextContent(/microphone/i)
    expect(screen.getByRole('alert')).toHaveTextContent(/address bar|browser settings/i)
  })

  it.each([
    ['user_stop', /stopped/i],
    ['silence_timeout', /15 seconds/i],
    ['max_duration', /5-minute/i],
  ] as const)('ended (%s) explains why in plain words', (reason, pattern) => {
    current = {
      ...current,
      state: 'ended',
      outcome: { kind: 'nothing', reason },
    }
    render(<Recorder />)
    expect(screen.getByRole('status')).toHaveTextContent(pattern)
  })

  it('shows a waking-up hint when connecting is slow', () => {
    current = { ...current, state: 'connecting', slowConnect: true }
    render(<Recorder />)
    expect(screen.getByText(/waking up/i)).toBeInTheDocument()
  })
})

describe('Recorder outcomes (US2)', () => {
  const entry = {
    id: '1',
    text: 'hello',
    languages: ['en'],
    engine: 'm',
    source: 'spoken' as const,
    status: 'complete' as const,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  it('confirms when the entry was saved', () => {
    current = {
      ...current,
      state: 'ended',
      segments: ['hello'],
      outcome: { kind: 'saved', reason: 'user_stop', transcription: entry },
    }
    render(<Recorder />)
    expect(screen.getByRole('status')).toHaveTextContent(/saved/i)
  })

  it('says nothing was captured and offers to start again', () => {
    current = { ...current, state: 'ended', outcome: { kind: 'nothing', reason: 'user_stop' } }
    render(<Recorder />)
    expect(screen.getByRole('status')).toHaveTextContent(/nothing was captured/i)
    expect(screen.getByRole('button', { name: /start again/i })).toBeInTheDocument()
  })

  it('keeps text on screen when saving failed', () => {
    current = {
      ...current,
      state: 'ended',
      outcome: { kind: 'unsaved', reason: 'user_stop', text: 'keep this text' },
    }
    render(<Recorder />)
    expect(screen.getByText('keep this text')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(/could not be saved/i)
  })

  it('keeps the text and says the connection was lost', () => {
    current = {
      ...current,
      state: 'error',
      segments: ['half a sentence'],
      error: { code: 'connection_lost', message: 'The connection was lost. The text below is still shown.' },
    }
    render(<Recorder />)
    expect(screen.getByText(/half a sentence/)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/connection was lost/i)
  })
})

describe('Recorder limits (FR-026)', () => {
  it('disables Start and says when recording is possible again when the quota is used up', () => {
    quotaValue = { limit: 10, remaining: 0, resets_at: '2026-01-01T13:30:00Z' }
    render(<Recorder />)
    expect(screen.getByRole('button', { name: /start/i })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent(/10 recordings/i)
    expect(screen.getByRole('status')).toHaveTextContent(/try again/i)
  })

  it('shows the retry time after a rate_limited error', () => {
    current = {
      ...current,
      state: 'error',
      error: { code: 'rate_limited', message: 'Hourly limit reached.', retry_at: '2026-01-01T13:30:00Z' },
    }
    render(<Recorder />)
    expect(screen.getByRole('alert')).toHaveTextContent(/hourly limit reached/i)
    expect(screen.getByRole('alert')).toHaveTextContent(/try again at/i)
  })

  it('shows how many recordings are left', () => {
    quotaValue = { limit: 10, remaining: 7, resets_at: null }
    render(<Recorder />)
    expect(screen.getByText(/7 of 10 recordings left/i)).toBeInTheDocument()
  })
})

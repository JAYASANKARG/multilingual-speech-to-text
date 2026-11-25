import { useEffect, useState } from 'react'
import type { EndReason } from '../../api/types'
import { displayText, type Outcome, type SessionError, type UiState } from '../../hooks/transcriptReducer'
import { useLanguages } from '../../hooks/useLanguages'
import { useQuota } from '../../hooks/useQuota'
import { useTranscriber } from '../../hooks/useTranscriber'
import { hasConsent, saveConsent } from '../../lib/consent'
import { AlertIcon, MicIcon, StopIcon } from '../icons'
import PrivacyNotice from '../PrivacyNotice'
import LanguagePicker from './LanguagePicker'
import LevelRibbon from './LevelRibbon'
import './Recorder.css'

const BADGE: Record<UiState, string> = {
  idle: 'Ready',
  connecting: 'Connecting',
  listening: 'Listening',
  processing: 'Finishing',
  ended: 'Ended',
  error: 'Error',
}

function reasonText(reason: EndReason): string {
  switch (reason) {
    case 'user_stop':
      return 'Stopped.'
    case 'silence_timeout':
      return 'Stopped after 15 seconds of silence.'
    case 'max_duration':
      return 'Reached the 5-minute limit.'
    case 'upstream_error':
      return 'The speech service had a problem, so the session ended early.'
    case 'client_disconnect':
      return 'The connection was lost.'
  }
}

function outcomeText(outcome: Outcome): string {
  const base = reasonText(outcome.reason)
  switch (outcome.kind) {
    case 'saved':
      return `${base} Saved to your history${outcome.transcription.status === 'interrupted' ? ' (marked interrupted)' : ''}.`
    case 'nothing':
      return `${base} Nothing was captured, so nothing was saved.`
    case 'unsaved':
      return `${base} Your text could not be saved, but it is still shown here.`
  }
}

function errorHelp(error: SessionError): string {
  switch (error.code) {
    case 'mic_denied':
      return `${error.message} Click the lock or microphone icon in the address bar (or open your browser settings), allow microphone access for this site, then press Start again.`
    case 'mic_unavailable':
      return `${error.message} Plug in or enable a microphone, then try again.`
    default:
      return error.message
  }
}

export default function Recorder({ onSaved }: { onSaved?: () => void }) {
  const t = useTranscriber()
  const languages = useLanguages()
  const { quota, refresh: refreshQuota } = useQuota()
  const [language, setLanguage] = useState('auto')
  const [askConsent, setAskConsent] = useState(false)
  const savedKind = t.outcome?.kind
  useEffect(() => {
    if (savedKind === 'saved') onSaved?.()
  }, [savedKind, onSaved])
  const finished = t.state === 'ended' || t.state === 'error'
  useEffect(() => {
    if (finished) void refreshQuota()
  }, [finished, refreshQuota])
  const exhausted = quota !== null && quota.remaining === 0
  const busy = t.state === 'connecting' || t.state === 'listening' || t.state === 'processing'
  const text = displayText(t)

  const begin = () => {
    void t.start(language)
  }
  const onStart = () => {
    if (hasConsent()) begin()
    else setAskConsent(true)
  }

  return (
    <div className="recorder">
      <div className="recorder-head">
        <div>
          <p className="eyebrow eyebrow-console">Session</p>
          <h2 className="recorder-sub">Live multilingual dictation</h2>
        </div>
        <span className={`tally tally-${t.state}`} aria-live="polite">
          <span className="tally-dot" aria-hidden="true" />
          {BADGE[t.state]}
        </span>
      </div>

      <div className="recorder-top">
        <LanguagePicker
          languages={languages}
          value={language}
          onChange={setLanguage}
          disabled={busy}
        />
        <div className="console-note">
          <span className="console-note-label">Max</span>
          <span className="console-note-value">05:00</span>
        </div>
      </div>

      <div className={`transcript-screen${t.state === 'listening' ? ' is-listening' : ''}`}>
        <div className="transcript-head">
          <span className="eyebrow eyebrow-console">Live transcript</span>
          <LevelRibbon levelRef={t.levelRef} active={t.state === 'listening'} />
        </div>
        <div className="transcript" aria-live="polite" aria-label="Live transcript">
          {text === '' && busy && <span className="placeholder">Start speaking…</span>}
          {text === '' && !busy && (
            <span className="placeholder">
              Press start, then speak. Hindi, English, or both in one sentence.
            </span>
          )}
          {t.segments.filter(Boolean).map((segment, i) => (
            <span key={i} className="final">
              {segment}{' '}
            </span>
          ))}
          {t.inProgress && <span className="interim">{t.inProgress}</span>}
        </div>
      </div>

      <div className="recorder-controls">
        {busy ? (
          <button
            className="primary record-button"
            onClick={t.stop}
            disabled={t.state === 'processing'}
          >
            <StopIcon />
            Stop
          </button>
        ) : (
          <button className="primary record-button" onClick={onStart} disabled={exhausted}>
            <MicIcon />
            {t.state === 'idle' ? 'Start' : 'Start again'}
          </button>
        )}
        <div className="recorder-status">
          {quota && !exhausted && (
            <>
              <div className="quota" aria-hidden="true">
                {Array.from({ length: quota.limit }, (_, i) => (
                  <span key={i} className={`quota-dot${i < quota.remaining ? ' on' : ''}`} />
                ))}
              </div>
              <p className="quota-text">
                {quota.remaining} of {quota.limit} recordings left this hour
              </p>
            </>
          )}
        </div>
      </div>

      <div className="recorder-hints" aria-hidden="true">
        <span>Up to 5 minutes</span>
        <span>Auto-saves on stop</span>
        <span>15 s silence stop</span>
      </div>

      {exhausted && (
        <p role="status" className="message message-console">
          You have used all {quota.limit} recordings for this hour.
          {quota.resets_at && ` Try again at ${new Date(quota.resets_at).toLocaleTimeString()}.`} You can
          still browse and edit your history.
        </p>
      )}

      {t.state === 'connecting' && t.slowConnect && (
        <p className="hint">Waking up the server… this can take up to a minute.</p>
      )}

      {t.error && (
        <p role="alert" className="message message-console error">
          <AlertIcon className="message-icon" />
          {errorHelp(t.error)}
          {t.error.retry_at && ` You can try again at ${new Date(t.error.retry_at).toLocaleTimeString()}.`}
        </p>
      )}
      {t.outcome && (
        <p role="status" className="message message-console">
          {outcomeText(t.outcome)}
        </p>
      )}
      {t.outcome?.kind === 'unsaved' && <p className="unsaved">{t.outcome.text}</p>}

      {askConsent && (
        <PrivacyNotice
          onAccept={() => {
            saveConsent()
            setAskConsent(false)
            begin()
          }}
          onDecline={() => setAskConsent(false)}
        />
      )}
    </div>
  )
}

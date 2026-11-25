import { useEffect, useState } from 'react'
import type { EndReason } from '../../api/types'
import { displayText, type Outcome, type SessionError, type UiState } from '../../hooks/transcriptReducer'
import { useLanguages } from '../../hooks/useLanguages'
import { useQuota } from '../../hooks/useQuota'
import { useTranscriber } from '../../hooks/useTranscriber'
import { hasConsent, saveConsent } from '../../lib/consent'
import PrivacyNotice from '../PrivacyNotice'
import LanguagePicker from './LanguagePicker'
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
      <LanguagePicker languages={languages} value={language} onChange={setLanguage} disabled={busy} />
      <div className="recorder-controls">
        {busy ? (
          <button className="primary" onClick={t.stop} disabled={t.state === 'processing'}>
            Stop
          </button>
        ) : (
          <button className="primary" onClick={onStart} disabled={exhausted}>
            {t.state === 'idle' ? 'Start' : 'Start again'}
          </button>
        )}
        <span className={`badge badge-${t.state}`}>{BADGE[t.state]}</span>
      </div>

      {exhausted && (
        <p role="status" className="message">
          You have used all {quota.limit} recordings for this hour.
          {quota.resets_at && ` Try again at ${new Date(quota.resets_at).toLocaleTimeString()}.`} You can
          still browse and edit your history.
        </p>
      )}
      {quota && !exhausted && (
        <p className="hint">
          {quota.remaining} of {quota.limit} recordings left this hour
        </p>
      )}

      {t.state === 'connecting' && t.slowConnect && (
        <p className="hint">Waking up the server… this can take up to a minute.</p>
      )}

      <div className="transcript" aria-live="polite" aria-label="Live transcript">
        {text === '' && busy && <span className="placeholder">Start speaking…</span>}
        {t.segments.filter(Boolean).map((segment, i) => (
          <span key={i} className="final">
            {segment}{' '}
          </span>
        ))}
        {t.inProgress && <span className="interim">{t.inProgress}</span>}
      </div>

      {t.error && (
        <p role="alert" className="message error">
          {errorHelp(t.error)}
          {t.error.retry_at && ` You can try again at ${new Date(t.error.retry_at).toLocaleTimeString()}.`}
        </p>
      )}
      {t.outcome && (
        <p role="status" className="message">
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

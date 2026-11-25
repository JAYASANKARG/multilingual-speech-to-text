import { useState } from 'react'
import type { Transcription } from '../../api/types'
import ConfirmDialog from '../ConfirmDialog'
import Modal from '../Modal'
import ExportActions from './ExportActions'
import './EntryDialog.css'

interface Props {
  /** null = create a new manual entry */
  entry: Transcription | null
  onSave: (text: string) => Promise<void>
  onDelete?: () => Promise<void>
  onClose: () => void
}

const fmt = (iso: string) => new Date(iso).toLocaleString()

export default function EntryDialog({ entry, onSave, onDelete, onClose }: Props) {
  const creating = entry === null
  const [editing, setEditing] = useState(creating)
  const [draft, setDraft] = useState(entry?.text ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const save = async () => {
    if (draft.trim() === '') {
      setError('Text cannot be empty.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await onSave(draft)
      if (creating) onClose()
      else setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save.')
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!onDelete) return
    setBusy(true)
    try {
      await onDelete()
      onClose()
    } catch (err) {
      setConfirming(false)
      setError(err instanceof Error ? err.message : 'Could not delete.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal labelledBy="entry-title" onClose={onClose}>
      <header className="entry-head">
        <p className="eyebrow">{creating ? 'Manual entry' : 'Saved transcript'}</p>
        <h2 id="entry-title">{creating ? 'Add entry' : 'Transcription'}</h2>
      </header>

      {entry && (
        <dl className="meta">
          <div className="meta-item">
            <dt>Created</dt>
            <dd>{fmt(entry.created_at)}</dd>
          </div>
          <div className="meta-item">
            <dt>Last modified</dt>
            <dd>{fmt(entry.updated_at)}</dd>
          </div>
          <div className="meta-item meta-wide">
            <dt>Languages</dt>
            <dd className="meta-chips">
              {entry.languages.map((l) => (
                <span key={l} className="chip">
                  {l}
                </span>
              ))}
            </dd>
          </div>
          <div className="meta-item meta-wide">
            <dt>Engine</dt>
            <dd>{entry.engine ?? 'Typed by hand'}</dd>
          </div>
          {entry.status === 'interrupted' && (
            <div className="meta-item meta-wide">
              <dt>Status</dt>
              <dd className="meta-warn">
                Interrupted (saved before the session ended normally)
              </dd>
            </div>
          )}
        </dl>
      )}

      {editing ? (
        <textarea
          className="entry-editor"
          aria-label="Transcription text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={busy}
          maxLength={50000}
          autoFocus={creating}
        />
      ) : (
        <div className="entry-read">
          <p className="entry-text">{entry?.text}</p>
          {entry && <ExportActions text={entry.text} createdAt={entry.created_at} />}
        </div>
      )}

      {error && (
        <p role="alert" className="message error">
          {error}
        </p>
      )}

      <div className="modal-actions">
        {editing ? (
          <>
            <button
              onClick={() => {
                if (creating) onClose()
                else {
                  setEditing(false)
                  setDraft(entry.text)
                  setError(null)
                }
              }}
              disabled={busy}
            >
              Cancel
            </button>
            <button className="primary" onClick={save} disabled={busy}>
              Save
            </button>
          </>
        ) : (
          <>
            {onDelete && (
              <button className="danger entry-delete" onClick={() => setConfirming(true)}>
                Delete
              </button>
            )}
            <button onClick={() => setEditing(true)}>Edit</button>
            <button className="primary" onClick={onClose}>
              Close
            </button>
          </>
        )}
      </div>

      {confirming && (
        <ConfirmDialog
          title="Delete this entry?"
          message="This will permanently delete the transcription. It cannot be undone."
          confirmLabel="Delete permanently"
          busy={busy}
          onConfirm={remove}
          onCancel={() => setConfirming(false)}
        />
      )}
    </Modal>
  )
}

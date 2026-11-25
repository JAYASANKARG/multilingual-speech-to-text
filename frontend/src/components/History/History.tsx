import type { Transcription } from '../../api/types'
import './History.css'

interface Props {
  items: Transcription[]
  loading: boolean
  loadingMore: boolean
  error: string | null
  hasMore: boolean
  filtered: boolean
  onOpen: (entry: Transcription) => void
  onLoadMore: () => void
  onRetry: () => void
  onAdd: () => void
  onClearFilters: () => void
}

const fmt = (iso: string) => new Date(iso).toLocaleString()

export default function History(p: Props) {
  return (
    <div className="history">
      <div className="history-toolbar">
        <button onClick={p.onAdd}>Add entry</button>
      </div>

      {p.loading && p.items.length === 0 && <p role="status">Loading history…</p>}

      {p.error && (
        <div role="alert" className="message error">
          {p.error} <button onClick={p.onRetry}>Retry</button>
        </div>
      )}

      {!p.loading && !p.error && p.items.length === 0 && (
        <p className="empty">
          {p.filtered ? (
            <>
              No results. <button onClick={p.onClearFilters}>Clear search</button>
            </>
          ) : (
            'No transcriptions yet. Record your first one above, or add an entry by hand.'
          )}
        </p>
      )}

      {p.items.length > 0 && (
        <ul className="history-list">
          {p.items.map((entry) => (
            <li key={entry.id}>
              <button className="history-row" onClick={() => p.onOpen(entry)}>
                <span className="preview">{entry.text}</span>
                <span className="row-meta">
                  <time dateTime={entry.created_at}>{fmt(entry.created_at)}</time>
                  {entry.languages.map((l) => (
                    <span key={l} className="chip">
                      {l}
                    </span>
                  ))}
                  <span className="engine">{entry.engine ?? 'Typed'}</span>
                  {entry.status === 'interrupted' && <span className="chip warn">Interrupted</span>}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {p.hasMore && (
        <button className="load-more" onClick={p.onLoadMore} disabled={p.loadingMore}>
          {p.loadingMore ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  )
}

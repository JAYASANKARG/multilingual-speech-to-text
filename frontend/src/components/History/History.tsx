import type { Language, Transcription } from '../../api/types'
import { ChevronRightIcon, PlusIcon } from '../icons'
import SearchBar from './SearchBar'
import './History.css'

interface Props {
  items: Transcription[]
  loading: boolean
  loadingMore: boolean
  error: string | null
  hasMore: boolean
  filtered: boolean
  languages?: Language[]
  q?: string
  language?: string
  onQueryChange?: (q: string) => void
  onLanguageChange?: (code: string) => void
  onOpen: (entry: Transcription) => void
  onLoadMore: () => void
  onRetry: () => void
  onAdd: () => void
  onClearFilters: () => void
}

const dateOf = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })

const timeOf = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })

export default function History(p: Props) {
  const showSearch =
    p.languages !== undefined && !!p.onQueryChange && !!p.onLanguageChange

  return (
    <div className="history">
      <div className="history-head">
        <div className="history-title">
          <p className="eyebrow">Archive</p>
          <h2 id="history-h">History</h2>
        </div>
        <button className="add-entry" onClick={p.onAdd}>
          <PlusIcon />
          Add entry
        </button>
      </div>

      {showSearch && (
        <SearchBar
          languages={p.languages!}
          q={p.q ?? ''}
          language={p.language ?? ''}
          onQueryChange={p.onQueryChange!}
          onLanguageChange={p.onLanguageChange!}
          onClear={p.onClearFilters}
        />
      )}

      {p.loading && p.items.length === 0 && (
        <div className="history-loading">
          <p role="status">Loading history…</p>
          <div className="skeleton-list" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <span key={i} className="skeleton-row" style={{ animationDelay: `${i * 90}ms` }} />
            ))}
          </div>
        </div>
      )}

      {p.error && (
        <div role="alert" className="message error history-error">
          <span>{p.error}</span>
          <button className="ghost" onClick={p.onRetry}>
            Retry
          </button>
        </div>
      )}

      {!p.loading && !p.error && p.items.length === 0 && (
        <div className="empty">
          <span className="empty-mark" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </span>
          {p.filtered ? (
            <>
              <p className="empty-title">No results.</p>
              <p className="empty-body">
                Nothing matches this search. <button onClick={p.onClearFilters}>Clear search</button>
              </p>
            </>
          ) : (
            <>
              <p className="empty-title">The ledger is empty.</p>
              <p className="empty-body">
                Record your first one above, or add an entry by hand.
              </p>
            </>
          )}
        </div>
      )}

      {p.items.length > 0 && (
        <>
          <p className="history-count">
            {p.items.length} {p.items.length === 1 ? 'entry' : 'entries'}
            {p.filtered ? ' matching' : ''}
          </p>
          <ul className="history-list">
            {p.items.map((entry) => (
              <li key={entry.id}>
                <button className="history-row" onClick={() => p.onOpen(entry)}>
                  <span className="row-stamp">
                    <time className="stamp-date" dateTime={entry.created_at}>
                      {dateOf(entry.created_at)}
                    </time>
                    <span className="stamp-time">{timeOf(entry.created_at)}</span>
                  </span>
                  <span className="row-body">
                    <span className="preview">{entry.text}</span>
                    <span className="row-meta">
                      {entry.languages.map((l) => (
                        <span key={l} className="chip">
                          {l}
                        </span>
                      ))}
                      <span className="engine">{entry.engine ?? 'Typed'}</span>
                      {entry.status === 'interrupted' && (
                        <span className="chip warn">Interrupted</span>
                      )}
                    </span>
                  </span>
                  <ChevronRightIcon className="row-chevron" />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {p.hasMore && (
        <button className="load-more" onClick={p.onLoadMore} disabled={p.loadingMore}>
          {p.loadingMore ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  )
}

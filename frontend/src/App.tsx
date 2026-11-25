import { useState } from 'react'
import './App.css'
import type { Transcription } from './api/types'
import EntryDialog from './components/EntryDialog/EntryDialog'
import History from './components/History/History'
import { BrandGlyph, ShieldIcon } from './components/icons'
import Recorder from './components/Recorder/Recorder'
import { useHistory } from './hooks/useHistory'
import { useLanguages } from './hooks/useLanguages'

type Dialog = { kind: 'entry'; entry: Transcription } | { kind: 'new' } | null

export default function App() {
  const history = useHistory()
  const languages = useLanguages()
  const [dialog, setDialog] = useState<Dialog>(null)

  return (
    <div className="app">
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <BrandGlyph />
          </span>
          <div className="brand-copy">
            <p className="brand-eyebrow">Multilingual · Live</p>
            <h1>Speech to Text</h1>
            <p className="tagline">Speak Hindi, English, or both. Watch it become text.</p>
          </div>
        </div>
        <div className="masthead-meta">
          <span className="engine-tag">
            <span className="engine-dot" aria-hidden="true" />
            Gemini Live
          </span>
        </div>
      </header>

      <main className="workspace">
        <section aria-label="Recorder" className="recorder-panel">
          <Recorder onSaved={history.refresh} />
        </section>
        <section aria-labelledby="history-h" className="panel history-panel">
          <History
            items={history.items}
            loading={history.loading}
            loadingMore={history.loadingMore}
            error={history.error}
            hasMore={history.hasMore}
            filtered={history.filtered}
            languages={languages}
            q={history.q}
            language={history.language}
            onQueryChange={history.setQuery}
            onLanguageChange={history.setLanguage}
            onOpen={(entry) => setDialog({ kind: 'entry', entry })}
            onLoadMore={history.loadMore}
            onRetry={history.refresh}
            onAdd={() => setDialog({ kind: 'new' })}
            onClearFilters={history.clearFilters}
          />
        </section>
      </main>

      <footer className="footer">
        <span className="footer-note">
          <ShieldIcon className="icon footer-icon" />
          Audio is streamed for transcription and never stored.
        </span>
        <span className="footer-tech">FastAPI · Gemini Live · PostgreSQL</span>
      </footer>

      {dialog?.kind === 'new' && (
        <EntryDialog entry={null} onSave={history.add} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === 'entry' && (
        <EntryDialog
          key={dialog.entry.id}
          entry={dialog.entry}
          onSave={async (text) => {
            const updated = await history.update(dialog.entry.id, text)
            setDialog({ kind: 'entry', entry: updated })
          }}
          onDelete={() => history.remove(dialog.entry.id)}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  )
}

import { useState } from 'react'
import './App.css'
import type { Transcription } from './api/types'
import EntryDialog from './components/EntryDialog/EntryDialog'
import History from './components/History/History'
import SearchBar from './components/History/SearchBar'
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
      <header className="app-header">
        <h1>Speech to Text</h1>
        <p className="tagline">Speak in Hindi, English, or both. Watch it appear live.</p>
      </header>
      <main className="app-main">
        <section aria-labelledby="recorder-h" className="card">
          <h2 id="recorder-h">Record</h2>
          <Recorder onSaved={history.refresh} />
        </section>
        <section aria-labelledby="history-h" className="card">
          <h2 id="history-h">History</h2>
          <SearchBar
            languages={languages}
            q={history.q}
            language={history.language}
            onQueryChange={history.setQuery}
            onLanguageChange={history.setLanguage}
            onClear={history.clearFilters}
          />
          <History
            items={history.items}
            loading={history.loading}
            loadingMore={history.loadingMore}
            error={history.error}
            hasMore={history.hasMore}
            filtered={history.filtered}
            onOpen={(entry) => setDialog({ kind: 'entry', entry })}
            onLoadMore={history.loadMore}
            onRetry={history.refresh}
            onAdd={() => setDialog({ kind: 'new' })}
            onClearFilters={history.clearFilters}
          />
        </section>
      </main>

      {dialog?.kind === 'new' && (
        <EntryDialog
          entry={null}
          onSave={history.add}
          onClose={() => setDialog(null)}
        />
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

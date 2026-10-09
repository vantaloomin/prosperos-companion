import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { bookSummary, entryWhen, type LoreBook } from './loreText'

const LORE_KEY = ['lore']

/** Imported lorebooks: the companion's own and the world's, each book and entry with an on/off switch. */
export function Lore() {
  const client = useQueryClient()
  const books = useQuery({ queryKey: LORE_KEY, queryFn: () => api<{ books: LoreBook[] }>('/lore').then((data) => data.books) })
  const [error, setError] = useState('')
  const [removing, setRemoving] = useState<LoreBook | null>(null)
  const change = async (path: string, body?: unknown, method?: string) => {
    setError('')
    try {
      client.setQueryData(LORE_KEY, (await api<{ books: LoreBook[] }>(path, body, method)).books)
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nothing was changed.')
      return false
    }
  }
  if (!books.data?.length) return null
  return (
    <section className="settings-section form-stack" aria-labelledby="lore-heading">
      <div>
        <h2 id="lore-heading">Lore</h2>
        <p className="subtle">Facts from imported lorebooks. An entry joins a reply when one of its words comes up in the last few messages; always-on entries are part of every reply.</p>
      </div>
      {books.data.map((book) => (
        <details key={book.id} className="lore-book">
          <summary><strong>{book.name}</strong> <span className="subtle">{bookSummary(book)}</span></summary>
          <div className="form-actions">
            <label className="check-row"><input type="checkbox" checked={book.enabled} onChange={(event) => void change(`/lore/books/${book.id}`, { enabled: event.target.checked }, 'PUT')} /> Use this lorebook</label>
            <button type="button" className="text-button" onClick={() => setRemoving(book)}>Remove…</button>
          </div>
          <ul className="network-list">
            {book.entries.map((entry) => (
              <li key={entry.id}>
                <label className="check-row">
                  <input type="checkbox" checked={entry.enabled} disabled={entry.pattern || !book.enabled} onChange={(event) => void change(`/lore/entries/${entry.id}`, { enabled: event.target.checked }, 'PUT')} />
                  <strong>{entry.title}</strong>
                </label>
                <span className="subtle">{entryWhen(entry)}.</span>
                <p>{entry.text.length > 400 ? `${entry.text.slice(0, 400)}…` : entry.text}</p>
              </li>
            ))}
          </ul>
        </details>
      ))}
      {error && <Notice tone="error">{error}</Notice>}
      {removing && <ConfirmDialog title={`Remove ${removing.name}?`} onClose={() => setRemoving(null)} actions={<>
        <button type="button" className="button" onClick={() => setRemoving(null)}>Cancel</button>
        <button type="button" className="button primary" onClick={() => void change(`/lore/books/${removing.id}`, undefined, 'DELETE').then((done) => done && setRemoving(null))}>Remove</button>
      </>}>
        <p>Its {removing.entries.length} entries leave every reply from now on. Import the file again to bring them back.</p>
      </ConfirmDialog>}
    </section>
  )
}

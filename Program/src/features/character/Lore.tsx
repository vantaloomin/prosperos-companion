import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { api } from '../../api'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { bookSummary, entryWhen, MOMENT_KINDS, type LoreBook, type LoreEntry, type MomentChoices } from './loreText'

const LORE_KEY = ['lore']
interface Listing { books: LoreBook[]; choices: MomentChoices }

/** The moments an entry comes up in besides its words (companion/lore_moments.py): chips to take off, and a picker
 * to add another, with no free text. */
function MomentPicker({ entry, choices, disabled, onChange }: {
  entry: LoreEntry; choices: MomentChoices; disabled: boolean; onChange: (keys: string[]) => void
}) {
  const keys = entry.when.map((moment) => moment.key)
  return (
    <div className="lore-moments" role="group" aria-label={`When ${entry.title} comes up`}>
      {entry.when.length > 0 && <ul className="moment-chips">
        {entry.when.map((moment) => (
          <li key={moment.key}>
            {moment.label}
            <button type="button" className="moment-remove" disabled={disabled} aria-label={`Take off ${moment.label}`}
              onClick={() => onChange(keys.filter((key) => key !== moment.key))}><X aria-hidden="true" /></button>
          </li>
        ))}
      </ul>}
      <select className="moment-add" value="" disabled={disabled} aria-label={`Add a moment for ${entry.title}`}
        onChange={(event) => event.target.value && onChange([...keys, event.target.value])}>
        <option value="">{entry.when.length ? 'Add another moment…' : 'Add a moment…'}</option>
        {MOMENT_KINDS.map(({ kind, label }) => {
          const left = (choices[kind] ?? []).filter((choice) => !keys.includes(choice.key))
          return left.length ? <optgroup key={kind} label={label}>
            {left.map((choice) => <option key={choice.key} value={choice.key}>{choice.label}</option>)}
          </optgroup> : null
        })}
      </select>
      {entry.when_guessed && <span className="subtle">Read from its keywords</span>}
    </div>
  )
}

/** Lorebooks: the companion's own, the world's and the city's, each book and entry with an on/off switch, and each
 * entry's moments. */
export function Lore() {
  const client = useQueryClient()
  const lore = useQuery({ queryKey: LORE_KEY, queryFn: () => api<Listing>('/lore') })
  const [error, setError] = useState('')
  const [removing, setRemoving] = useState<LoreBook | null>(null)
  const change = async (path: string, body?: unknown, method?: string) => {
    setError('')
    try {
      client.setQueryData(LORE_KEY, await api<Listing>(path, body, method))
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Nothing was changed.')
      return false
    }
  }
  const books = lore.data?.books
  if (!books?.length || !lore.data) return null
  const choices = lore.data.choices
  return (
    <section className="settings-section form-stack" aria-labelledby="lore-heading">
      <div>
        <h2 id="lore-heading">Lore</h2>
        <p className="subtle">Facts from lorebooks and from the city they live in. An entry joins a reply when one of its words comes up in the last few messages, or when the moment fits: the weather, the time of day, a holiday, a place, being at work. Always-on entries are part of every reply.</p>
      </div>
      {books.map((book) => (
        <details key={book.id} className="lore-book">
          <summary><strong>{book.name}</strong> <span className="subtle">{bookSummary(book)}</span></summary>
          {book.city && book.description && <p className="subtle lore-credit">{book.description}</p>}
          <div className="form-actions">
            <label className="check-row"><input type="checkbox" checked={book.enabled} onChange={(event) => void change(`/lore/books/${book.id}`, { enabled: event.target.checked }, 'PUT')} /> Use this lorebook</label>
            {!book.city && <button type="button" className="text-button" onClick={() => setRemoving(book)}>Remove…</button>}
          </div>
          <ul className="network-list">
            {book.entries.map((entry) => (
              <li key={entry.id}>
                <label className="check-row">
                  <input type="checkbox" checked={entry.enabled} disabled={entry.pattern || !book.enabled} onChange={(event) => void change(`/lore/entries/${entry.id}`, { enabled: event.target.checked }, 'PUT')} />
                  <strong>{entry.title}</strong>
                </label>
                {entry.fits_now && book.enabled && <span className="badge">Fits right now</span>}
                <span className="subtle lore-when">{entryWhen(entry)}.</span>
                <p>{entry.text.length > 400 ? `${entry.text.slice(0, 400)}…` : entry.text}</p>
                {!entry.always && !entry.pattern && <MomentPicker entry={entry} choices={choices} disabled={!book.enabled || !entry.enabled}
                  onChange={(keys) => void change(`/lore/entries/${entry.id}/when`, { when: keys }, 'PUT')} />}
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

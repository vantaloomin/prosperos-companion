import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookPlus, RefreshCw, Search } from 'lucide-react'
import { api } from '../../api'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Notice } from '../../components/Feedback'
import { fileData } from './helper'
import { LIBRARY_KEY, LIBRARY_MAX_BYTES, LIBRARY_TYPES, ONLINE_KEY, addedText, creditText, downloadedText, libraryIntro, librarySummary, shelfName, shownText, type LibraryBook, type OnlineBook, type Passage } from './libraryText'

type Result = { tone: 'info' | 'error'; text: string } | null
type Books = { books: LibraryBook[] }

/** The reference library: long texts the companion (or everyone in the world) can draw on. On the Character page
 * (`name`, the companion's books and the world's) and in Settings > Life & cities (`world`, the world's only). */
export function Library({ name, world = false }: { name?: string; world?: boolean }) {
  const client = useQueryClient()
  const books = useQuery({ queryKey: LIBRARY_KEY, queryFn: () => api<Books>('/library').then((data) => data.books) })
  const online = useQuery({ queryKey: ONLINE_KEY, queryFn: () => api<{ books: OnlineBook[] }>('/library/online').then((data) => data.books) })
  const [result, setResult] = useState<Result>(null)
  const [removing, setRemoving] = useState<LibraryBook | null>(null)
  const { input, busy, addFile } = useAddBook(world, shelfName(world, name), setResult)
  const change = async (path: string, body?: unknown, method?: string) => {
    setResult(null)
    try {
      client.setQueryData(LIBRARY_KEY, (await api<Books>(path, body, method)).books)
      void client.invalidateQueries({ queryKey: ONLINE_KEY })
      return true
    } catch (failure) {
      setResult({ tone: 'error', text: failure instanceof Error ? failure.message : 'Nothing was changed.' })
      return false
    }
  }
  const shown = (books.data ?? []).filter((book) => !world || book.world)
  const heading = world ? 'world-library-heading' : 'library-heading'
  return (
    <section className="settings-section form-stack" aria-labelledby={heading}>
      <div>
        <h2 id={heading}>Library</h2>
        <p className="subtle">{libraryIntro(world, name)}</p>
      </div>
      <input ref={input} type="file" accept={LIBRARY_TYPES} hidden onChange={(event) => void addFile(event.target.files?.[0])} />
      <div>
        <button type="button" className="button" disabled={busy} aria-describedby={`${heading}-types`} onClick={() => input.current?.click()}>
          <BookPlus aria-hidden="true" />{busy ? 'Reading…' : 'Add a book'}
        </button>
        <p className="subtle library-types" id={`${heading}-types`}>A .txt, .md, .html or .epub file, or a TiddlyWiki saved as one file. Up to 10 MB.</p>
      </div>
      <div aria-live="polite">{result && <Notice tone={result.tone}>{result.text}</Notice>}</div>
      {shown.map((book) => (
        <LibraryShelf key={book.id} book={book} online={online.data?.find((item) => item.key === book.online)}
          change={change} onRemove={() => setRemoving(book)} onResult={setResult} />
      ))}
      {removing && <ConfirmDialog title={`Remove ${removing.name}?`} onClose={() => setRemoving(null)} actions={<>
        <button type="button" className="button" onClick={() => setRemoving(null)}>Cancel</button>
        <button type="button" className="button primary" onClick={() => void change(`/library/books/${removing.id}`, undefined, 'DELETE').then((done) => done && setRemoving(null))}>Remove</button>
      </>}>
        <p>Its passages leave every reply from now on. {removing.online ? 'Add it again from its city in Settings > Life & cities.' : 'Add the file again to bring them back.'}</p>
      </ConfirmDialog>}
    </section>
  )
}

/** A file read in the browser and sent as a new book of the companion's library or the world's. */
function useAddBook(world: boolean, shelf: string, setResult: (result: Result) => void) {
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const addFile = async (file: File | undefined) => {
    if (!file) return
    setResult(null)
    if (file.size > LIBRARY_MAX_BYTES) {
      setResult({ tone: 'error', text: 'A book can be up to 10 MB. Split a longer text into parts and add each one.' })
      return
    }
    setBusy(true)
    try {
      const made = await api<Books & { added: { name: string; passages: number } }>('/library/books', { filename: file.name, data: await fileData(file), world })
      client.setQueryData(LIBRARY_KEY, made.books)
      setResult({ tone: 'info', text: addedText(made.added, shelf) })
    } catch (failure) {
      setResult({ tone: 'error', text: failure instanceof Error ? failure.message : 'That file could not be added.' })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  return { input, busy, addFile }
}

interface ShelfProps {
  book: LibraryBook
  online?: OnlineBook
  change: (path: string, body?: unknown, method?: string) => Promise<boolean>
  onRemove: () => void
  onResult: (result: Result) => void
}

/** One book: its switch, its credit when it came from its author's site, and its passages with a search. */
function LibraryShelf({ book, online, change, onRemove, onResult }: ShelfProps) {
  const [open, setOpen] = useState(false)
  return (
    <details className="lore-book library-book" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary><strong>{book.name}</strong> <span className="subtle">{librarySummary(book, online?.city_name)}</span></summary>
      {online && <p className="subtle library-credit">{creditText(online)} <a href={online.licence_url} target="_blank" rel="noreferrer">About the licence</a></p>}
      <div className="form-actions">
        <label className="check-row"><input type="checkbox" checked={book.enabled} onChange={(event) => void change(`/library/books/${book.id}`, { enabled: event.target.checked }, 'PUT')} /> Use this book</label>
        {online && <GetLatest online={online} onResult={onResult} />}
        <button type="button" className="text-button" onClick={onRemove}>Remove…</button>
      </div>
      {open && <Passages book={book} />}
    </details>
  )
}

function Passages({ book }: { book: LibraryBook }) {
  const [query, setQuery] = useState('')
  const [asked, setAsked] = useState('')
  const found = useQuery({
    queryKey: [...LIBRARY_KEY, book.id, book.updated_at, asked],
    queryFn: () => api<{ total: number; passages: Passage[] }>(`/library/books/${book.id}/passages?q=${encodeURIComponent(asked)}`),
  })
  const field = `library-search-${book.id}`
  return (
    <div className="library-passages">
      <form className="search-field" role="search" onSubmit={(event) => { event.preventDefault(); setAsked(query.trim()) }}>
        <Search aria-hidden="true" />
        <label className="visually-hidden" htmlFor={field}>Search {book.name}</label>
        <input id={field} type="search" placeholder="Search this book" value={query} onChange={(event) => { setQuery(event.target.value); if (!event.target.value) setAsked('') }} />
      </form>
      {found.data && <>
        <p className="subtle" aria-live="polite">{shownText(found.data.passages.length, found.data.total, Boolean(asked))}</p>
        <ul className="network-list">
          {found.data.passages.map((passage) => (
            <li key={passage.id}>
              {passage.title && <strong>{passage.title}</strong>}
              <p>{passage.text}</p>
            </li>
          ))}
        </ul>
      </>}
    </div>
  )
}

/** Download the book again from its author's site, replacing the old passages. */
export function GetLatest({ online, onResult, label }: { online: OnlineBook; onResult: (result: Result) => void; label?: string }) {
  const client = useQueryClient()
  const [busy, setBusy] = useState(false)
  const download = async () => {
    setBusy(true)
    onResult(null)
    try {
      const made = await api<{ added: { name: string; passages: number; replaced: boolean } }>(`/library/online/${online.key}`, {})
      onResult({ tone: 'info', text: downloadedText(made.added, online.author, online.city_name) })
      await Promise.all([LIBRARY_KEY, ONLINE_KEY].map((queryKey) => client.invalidateQueries({ queryKey })))
    } catch (failure) {
      onResult({ tone: 'error', text: failure instanceof Error ? failure.message : 'The download did not finish.' })
    } finally { setBusy(false) }
  }
  const text = label ?? (online.book_id ? `Get the latest from ${online.author}'s wiki` : `Add the ${online.name}`)
  return (
    <button type="button" className="text-button" disabled={busy} onClick={() => void download()}>
      {online.book_id ? <RefreshCw aria-hidden="true" /> : <BookPlus aria-hidden="true" />}{busy ? 'Downloading…' : text}
    </button>
  )
}

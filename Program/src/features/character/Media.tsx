import { useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Music, Pencil, RotateCcw, Tv } from 'lucide-react'
import { api } from '../../api'
import type { MediaNow, MediaView } from '../../types'
import { calendarDay } from '../../when.ts'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Field } from '../../components/Fields'
import { LATELY_SHOWN, MEDIA_KEY, byLabel, examples, itemNumbers, kindNoun, numbersLine, panelHeading, recommendedNote, titled, verdictSplit } from './mediaText'

type Feedback = { tone: 'info' | 'error'; text: string } | null
type Save = (body: object, done: string) => Promise<boolean>

const ICONS = { book: BookOpen, show: Tv, music: Music }

/** The book, show and song the companion is in the middle of, and what they finished lately: picked by the app, changeable here. */
export function Media({ name }: { name: string }) {
  const client = useQueryClient()
  const media = useQuery({ queryKey: MEDIA_KEY, queryFn: () => api<MediaView>('/life/media') })
  const [feedback, setFeedback] = useState<Feedback>(null)
  const save: Save = async (body, done) => {
    try {
      client.setQueryData(MEDIA_KEY, await api<MediaView>('/life/media', body, 'PATCH'))
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    }
  }
  const view = media.data
  return (
    <section className="home-panel media-panel" aria-labelledby="media-heading">
      <h2 id="media-heading">{panelHeading(name)}</h2>
      <p className="subtle">What they are in the middle of, picked from their tastes and their city's time and place. They move on to the next on their own; set one yourself and they start it today.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {media.isPending && <Loading label="Loading what they are into" />}
      {media.isError && <ErrorNotice error={media.error} />}
      {view?.off && <p className="subtle">Turned off in Settings › Realism › Their days.</p>}
      {view && !view.off && <>
        <ul className="media-now">{view.now.map((item) => <NowRow key={item.id} item={item} view={view} save={save} />)}</ul>
        {numbersLine(view) && <p className="subtle">{numbersLine(view)}</p>}
        {view.lately.length > 0 && <Lately view={view} />}
      </>}
    </section>
  )
}

/** A line with its title set off: italic for books and shows, quoted for songs. */
function Titled({ text, title, kind }: { text: string; title: string; kind: MediaNow['kind'] }): ReactNode {
  const parts = titled(text, title)
  if (!parts) return text
  const shown = kind === 'music' ? <q>{title}</q> : <cite>{title}</cite>
  return <>{parts[0]}{shown}{parts[1]}</>
}

function NowRow({ item, view, save }: { item: MediaNow; view: MediaView; save: Save }) {
  const [editing, setEditing] = useState(false)
  const Icon = ICONS[item.kind]
  const numbers = itemNumbers(view, item.id, item.kind)
  return (
    <li className="media-row">
      <Icon aria-hidden="true" className="media-icon" />
      <div className="media-body">
        <p><Titled text={item.text} title={item.title} kind={item.kind} />{item.set_by_you && <span className="badge media-mine">Set by you</span>}</p>
        {item.recommended && <p className="subtle"><Titled text={recommendedNote(item)} title={item.waiting ?? ''} kind="book" /></p>}
        {numbers && <p className="subtle">{numbers}</p>}
        {editing
          ? <ChangeForm item={item} bank={view.bank} save={save} onDone={() => setEditing(false)} />
          : !item.recommended && <div className="person-actions">
            <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Change {kindNoun(item.kind)}</button>
            {item.set_by_you && <button type="button" className="text-button" onClick={() => void save({ kind: item.kind, reset: true }, 'Back to a pick of their own.')}><RotateCcw aria-hidden="true" />Back to their own pick</button>}
          </div>}
      </div>
    </li>
  )
}

/** What ended lately: the newest few, the rest behind "Show N more". */
function Lately({ view }: { view: MediaView }) {
  const [all, setAll] = useState(false)
  const shown = all ? view.lately : view.lately.slice(0, LATELY_SHOWN)
  const hidden = view.lately.length - shown.length
  return (
    <div className="media-lately">
      <h3>Lately</h3>
      <ul className="diary-list">{shown.map((item) => {
        const [line, verdict] = verdictSplit(item.text)
        return <li key={item.id}><span className="kitchen-day">{calendarDay(item.ended_on)}</span>
          <span><Titled text={line} title={item.title} kind={item.kind} />{verdict && <span className="media-verdict"> — {verdict}</span>}</span></li>
      })}</ul>
      {hidden > 0 && <button type="button" className="text-button media-more" onClick={() => setAll(true)}>Show {hidden} more</button>}
    </div>
  )
}

function ChangeForm({ item, bank, save, onDone }: { item: MediaNow; bank?: string; save: Save; onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [by, setBy] = useState('')
  const example = examples(item.kind, bank)
  const second = byLabel(item.kind)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save({ kind: item.kind, title, by }, `Saved. They start ${title.trim()} today.`)) onDone()
  }
  return (
    <form className="form-stack media-form" onSubmit={(event) => void submit(event)} onKeyDown={(event) => { if (event.key === 'Escape') onDone() }}>
      <Field label="Title">{(id, describedBy) => (
        <input id={id} aria-describedby={describedBy} value={title} maxLength={120} required autoFocus placeholder={example.title} onChange={(event) => setTitle(event.target.value)} />
      )}</Field>
      {second && <Field label={second}>{(id, describedBy) => (
        <input id={id} aria-describedby={describedBy} value={by} maxLength={80} placeholder={example.by} onChange={(event) => setBy(event.target.value)} />
      )}</Field>}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={!title.trim()}>Save</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

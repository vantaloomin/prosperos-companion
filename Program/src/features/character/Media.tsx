import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Music, Pencil, RotateCcw, Tv } from 'lucide-react'
import { api } from '../../api'
import type { MediaNow, MediaView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { TextInput } from '../../components/Fields'
import { calendarDay } from '../../when.ts'
import { MEDIA_KEY, byLabel, itemNumbers, kindNoun, numbersLine } from './mediaText'

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
      <h2 id="media-heading">Reading, watching, listening</h2>
      <p className="subtle">What {name} is in the middle of, picked from their tastes and their city's time and place. They move on to the next on their own; set one yourself and they start it today.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {media.isPending && <Loading label="Loading what they are into" />}
      {media.isError && <ErrorNotice error={media.error} />}
      {view?.off && <p className="subtle">Turned off in Settings › Realism › Their days.</p>}
      {view && !view.off && <>
        <ul className="media-now">{view.now.map((item) => <NowRow key={item.id} item={item} view={view} save={save} />)}</ul>
        {numbersLine(view) && <p className="subtle">{numbersLine(view)}</p>}
        {view.lately.length > 0 && <div className="media-lately">
          <h3>Lately</h3>
          <ul className="diary-list">{view.lately.map((item) => <li key={item.id}><span className="kitchen-day">{calendarDay(item.ended_on)}</span><span>{item.text}</span></li>)}</ul>
        </div>}
      </>}
    </section>
  )
}

function NowRow({ item, view, save }: { item: MediaNow; view: MediaView; save: Save }) {
  const [editing, setEditing] = useState(false)
  const Icon = ICONS[item.kind]
  const numbers = itemNumbers(view, item.id)
  return (
    <li className="media-row">
      <Icon aria-hidden="true" className="media-icon" />
      <div className="media-body">
        <p>{item.text}{item.set_by_you && <span className="badge media-mine">Set by you</span>}</p>
        {item.on_hold && <p className="subtle">On hold while they get through {item.on_hold}, which you recommended.</p>}
        {numbers && <p className="subtle">{numbers}</p>}
        {editing
          ? <ChangeForm item={item} save={save} onDone={() => setEditing(false)} />
          : <div className="person-actions">
            <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Change {kindNoun(item.kind)}</button>
            {item.set_by_you && <button type="button" className="text-button" onClick={() => void save({ kind: item.kind, reset: true }, 'Back to a pick of their own.')}><RotateCcw aria-hidden="true" />Back to their own pick</button>}
          </div>}
      </div>
    </li>
  )
}

function ChangeForm({ item, save, onDone }: { item: MediaNow; save: Save; onDone: () => void }) {
  const [title, setTitle] = useState('')
  const [by, setBy] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save({ kind: item.kind, title, by }, `Saved. They start ${title.trim()} today.`)) onDone()
  }
  return (
    <form className="form-stack media-form" onSubmit={(event) => void submit(event)}>
      <TextInput label="Title" value={title} onChange={setTitle} maxLength={120} required />
      <TextInput label={byLabel(item.kind)} value={by} onChange={setBy} maxLength={80} />
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={!title.trim()}>Save</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

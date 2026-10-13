import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, Pencil, Plus, RotateCcw, Undo2 } from 'lucide-react'
import { api } from '../../api'
import type { HobbiesView, Hobby } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { HOBBIES_KEY, gaveUpLine, hobbyDate, hobbyNumbers, levelLabel, metaParts, recentLine, sourceText } from './hobbiesText'

type Act = (action: () => Promise<HobbiesView>, done: string | null) => Promise<boolean>
type Patch = (hobby: Hobby, body: object, done: string | null) => Promise<boolean>

/** The companion's pastimes (companion/life/hobbies.py): how far along they are in plain words, their latest
 * milestones, and the ones they gave up. The app decides; the user can add, keep, set how good, or give one up. */
export function Hobbies({ name }: { name: string }) {
  const client = useQueryClient()
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const hobbies = useQuery({ queryKey: HOBBIES_KEY, queryFn: () => api<HobbiesView>('/life/hobbies') })
  const act: Act = async (action, done) => {
    try {
      client.setQueryData(HOBBIES_KEY, await action())
      setFeedback(done ? { tone: 'info', text: done } : null)
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    }
  }
  const first = name.split(' ')[0]
  return (
    <section className="home-panel hobbies-panel" aria-labelledby="hobbies-heading">
      <h2 id="hobbies-heading">{first}'s pastimes</h2>
      <p className="subtle">What they do with their free time, from their interests and their city. They get better with practice, and some weeks one slides; how often depends on Settings &gt; Realism.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {hobbies.isPending && <Loading label="Loading their pastimes" />}
      {hobbies.isError && <ErrorNotice error={hobbies.error} />}
      {hobbies.data && <HobbyLists view={hobbies.data} name={name} act={act} />}
    </section>
  )
}

/** The pastimes going now, the add card, and the ones given up folded underneath. One just given up stays in
 * place as "Kim gave up rock climbing. Undo" until the next change. */
function HobbyLists({ view, name, act }: { view: HobbiesView; name: string; act: Act }) {
  const [adding, setAdding] = useState(false)
  const [undo, setUndo] = useState<string | null>(null)
  const first = name.split(' ')[0]
  const patch: Patch = async (hobby, body, done) => {
    setUndo(null)
    return act(() => api<HobbiesView>(`/life/hobbies/${hobby.id}`, body, 'PATCH'), done)
  }
  const giveUp = async (hobby: Hobby) => { if (await patch(hobby, { status: 'dropped' }, null)) setUndo(hobby.id) }
  const going = view.hobbies.filter((hobby) => hobby.status !== 'dropped' || hobby.id === undo)
  const dropped = view.hobbies.filter((hobby) => hobby.status === 'dropped' && hobby.id !== undo)
  const card = (hobby: Hobby) => hobby.id === undo
    ? <li key={hobby.id} className="person-card hobby-card hobby-undo">
      <p>{gaveUpLine(hobby, first)}</p>
      <button type="button" className="text-button" onClick={() => void patch(hobby, { status: 'active' }, null)}><Undo2 aria-hidden="true" />Undo</button>
    </li>
    : <HobbyCard key={hobby.id} hobby={hobby} view={view} name={first} patch={patch} giveUp={giveUp} />
  return <>
    {going.length === 0
      ? <p>{name} has no pastimes going right now.</p>
      : <ul className="person-list">{going.map(card)}</ul>}
    {adding
      ? <AddForm view={view} act={act} onDone={() => setAdding(false)} />
      : view.can_add && <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a pastime</button>}
    {dropped.length > 0 && (
      <details className="hobbies-dropped">
        <summary>Given up</summary>
        <ul className="person-list">{dropped.map(card)}</ul>
      </details>
    )}
  </>
}

function HobbyCard({ hobby, view, name, patch, giveUp }: { hobby: Hobby; view: HobbiesView; name: string; patch: Patch; giveUp: (hobby: Hobby) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const gone = hobby.status === 'dropped'
  const meta = metaParts(hobby, view.level_names)
  return (
    <li className={`person-card hobby-card${gone ? ' removed' : ''}`}>
      <header className="hobby-head">
        <h3>{hobby.label}</h3>
        <span className="badge hobby-source">{sourceText(hobby)}</span>
      </header>
      <p className="hobby-meta">{meta.level && <strong>{meta.level}</strong>}{meta.rest.map((part, index) => (
        <span key={part} className="subtle">{meta.level || index ? ' · ' : ''}{part}</span>
      ))}</p>
      {hobby.status === 'stalled' && <p className="pet-status hobby-stalled">{hobby.status_text}</p>}
      {hobbyNumbers(hobby) && <p className="subtle pet-numbers">{hobbyNumbers(hobby)}</p>}
      {hobby.recent.length > 0 && !gone && (
        <dl className="pet-recent">{hobby.recent.slice(0, 3).map((event) => (
          <div key={`${event.date}-${event.kind}-${event.text}`}><dt><time dateTime={event.date}>{hobbyDate(event.date)}</time></dt><dd>{recentLine(event.text, name)}</dd></div>
        ))}</dl>
      )}
      {editing
        ? <EditForm hobby={hobby} view={view} patch={patch} onDone={() => setEditing(false)} />
        : gone
          ? <div className="person-actions"><button type="button" className="text-button" onClick={() => void patch(hobby, { status: 'active' }, `${hobby.label} is back on, and will stay.`)}><RotateCcw aria-hidden="true" />Take it back up</button></div>
          : <div className="person-actions">
            <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Change</button>
            <button type="button" className="text-button" onClick={() => void giveUp(hobby)}><Archive aria-hidden="true" />Give it up</button>
          </div>}
    </li>
  )
}

function LevelSelect({ id, view, value, onChange, unset }: { id: string; view: HobbiesView; value: number; onChange: (value: number) => void; unset?: string }) {
  return <>
    <label htmlFor={id}>How good they are</label>
    <select id={id} value={value} onChange={(event) => onChange(Number(event.target.value))}>
      {unset && <option value={-1}>{unset}</option>}
      {view.level_names.map((text, index) => <option key={text} value={index}>{levelLabel(text)}</option>)}
    </select>
  </>
}

function EditForm({ hobby, view, patch, onDone }: { hobby: Hobby; view: HobbiesView; patch: Patch; onDone: () => void }) {
  const [level, setLevel] = useState(hobby.level)
  const [kept, setKept] = useState(hobby.kept)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const body: { level?: number; kept?: boolean } = {}
    if (level !== hobby.level) body.level = level
    if (kept !== hobby.kept) body.kept = kept
    if (!Object.keys(body).length) return onDone()
    if (await patch(hobby, body, 'Saved. The days ahead follow it.')) onDone()
  }
  return (
    <form className="rename-form hobby-form" onSubmit={(event) => void save(event)} onKeyDown={(event) => cancelOnEscape(event, onDone)}>
      <LevelSelect id={`hobby-level-${hobby.id}`} view={view} value={level} onChange={setLevel} />
      {hobby.source === 'app' && <Toggle label="Keep this one" checked={kept} onChange={setKept} hint="They won't give this one up on their own." />}
      <div className="rename-row">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AddForm({ view, act, onDone }: { view: HobbiesView; act: Act; onDone: () => void }) {
  const [name, setName] = useState('')
  const [level, setLevel] = useState(-1)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { input.current?.focus() }, [])
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) return
    const body = level >= 0 ? { name: clean, level } : { name: clean }
    if (await act(() => api<HobbiesView>('/life/hobbies', body), `Added ${clean}. They will never give it up on their own.`)) onDone()
  }
  return (
    <form className="person-card hobby-add" aria-labelledby="hobby-add-heading" onSubmit={(event) => void save(event)} onKeyDown={(event) => cancelOnEscape(event, onDone)}>
      <h3 id="hobby-add-heading">Add a pastime</h3>
      <div className="rename-form hobby-form">
        <label htmlFor="hobby-add-name">Pastime</label>
        <input ref={input} id="hobby-add-name" value={name} maxLength={40} placeholder="Pottery, chess, learning Spanish" onChange={(event) => setName(event.target.value)} />
        <LevelSelect id="hobby-add-level" view={view} value={level} onChange={setLevel} unset="Picked for them" />
        <div className="rename-row">
          <button type="submit" className="button primary">Add</button>
          <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
        </div>
      </div>
    </form>
  )
}

function cancelOnEscape(event: KeyboardEvent, onDone: () => void) {
  if (event.key === 'Escape') { event.preventDefault(); onDone() }
}

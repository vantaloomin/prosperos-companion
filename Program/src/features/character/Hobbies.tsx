import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { HobbiesView, Hobby } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { HOBBIES_KEY, hobbyDate, hobbyNumbers, levelLabel, recentLine, sourceText, statusLine } from './hobbiesText'

type Act = (action: () => Promise<HobbiesView>, done: string) => Promise<boolean>

/** The companion's pastimes (companion/life/hobbies.py): how far along they are in plain words, their latest
 * milestones, and the ones they gave up. The app decides; the user can add, keep, set how good, or give one up. */
export function Hobbies({ name }: { name: string }) {
  const client = useQueryClient()
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const hobbies = useQuery({ queryKey: HOBBIES_KEY, queryFn: () => api<HobbiesView>('/life/hobbies') })
  const act: Act = async (action, done) => {
    try {
      client.setQueryData(HOBBIES_KEY, await action())
      setFeedback({ tone: 'info', text: done })
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

/** The pastimes going now, the add button, and the ones given up folded underneath. */
function HobbyLists({ view, name, act }: { view: HobbiesView; name: string; act: Act }) {
  const [adding, setAdding] = useState(false)
  const first = name.split(' ')[0]
  const going = view.hobbies.filter((hobby) => hobby.status !== 'dropped')
  const dropped = view.hobbies.filter((hobby) => hobby.status === 'dropped')
  return <>
    {going.length === 0
      ? <p>{name} has no pastimes going right now.</p>
      : <ul className="person-list">{going.map((hobby) => <HobbyCard key={hobby.id} hobby={hobby} view={view} name={first} act={act} />)}</ul>}
    {adding
      ? <AddForm view={view} act={act} onDone={() => setAdding(false)} />
      : view.can_add && <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a pastime</button>}
    {dropped.length > 0 && (
      <details className="hobbies-dropped">
        <summary>Given up</summary>
        <ul className="person-list">{dropped.map((hobby) => <HobbyCard key={hobby.id} hobby={hobby} view={view} name={first} act={act} />)}</ul>
      </details>
    )}
  </>
}

function HobbyCard({ hobby, view, name, act }: { hobby: Hobby; view: HobbiesView; name: string; act: Act }) {
  const [editing, setEditing] = useState(false)
  const gone = hobby.status === 'dropped'
  return (
    <li className={`person-card hobby-card${gone ? ' removed' : ''}`}>
      <header>
        <p className="subtle">{sourceText(hobby)}</p>
        <h3>{hobby.label}</h3>
      </header>
      {!gone && <p className="hobby-level">{hobby.level_text}</p>}
      <p className={hobby.status === 'stalled' ? 'pet-status hobby-stalled' : 'subtle'}>{statusLine(hobby)}</p>
      {hobbyNumbers(hobby) && <p className="subtle pet-numbers">{hobbyNumbers(hobby)}</p>}
      {hobby.recent.length > 0 && !gone && (
        <dl className="pet-recent">{hobby.recent.slice(0, 3).map((event) => (
          <div key={`${event.date}-${event.kind}-${event.text}`}><dt><time dateTime={event.date}>{hobbyDate(event.date)}</time></dt><dd>{recentLine(event.text, name)}</dd></div>
        ))}</dl>
      )}
      {editing
        ? <EditForm hobby={hobby} view={view} act={act} onDone={() => setEditing(false)} />
        : <HobbyActions hobby={hobby} act={act} onEdit={() => setEditing(true)} />}
    </li>
  )
}

function HobbyActions({ hobby, act, onEdit }: { hobby: Hobby; act: Act; onEdit: () => void }) {
  const patch = (body: object, done: string) => act(() => api<HobbiesView>(`/life/hobbies/${hobby.id}`, body, 'PATCH'), done)
  if (hobby.status === 'dropped') {
    return <div className="person-actions"><button type="button" className="text-button" onClick={() => void patch({ status: 'active' }, `${hobby.label} is back on, and will stay.`)}><RotateCcw aria-hidden="true" />Take it back up</button></div>
  }
  return (
    <div className="person-actions">
      <button type="button" className="text-button" onClick={onEdit}><Pencil aria-hidden="true" />Change</button>
      <button type="button" className="text-button" onClick={() => void patch({ status: 'dropped' }, `They gave up ${hobby.name}.`)}><Trash2 aria-hidden="true" />Give it up</button>
    </div>
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

function EditForm({ hobby, view, act, onDone }: { hobby: Hobby; view: HobbiesView; act: Act; onDone: () => void }) {
  const [level, setLevel] = useState(hobby.level)
  const [kept, setKept] = useState(hobby.kept)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const body: { level?: number; kept?: boolean } = {}
    if (level !== hobby.level) body.level = level
    if (kept !== hobby.kept) body.kept = kept
    if (!Object.keys(body).length) return onDone()
    if (await act(() => api<HobbiesView>(`/life/hobbies/${hobby.id}`, body, 'PATCH'), 'Saved. The days ahead follow it.')) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <LevelSelect id={`hobby-level-${hobby.id}`} view={view} value={level} onChange={setLevel} />
      {hobby.source === 'app' && <Toggle label="Keep this one" checked={kept} onChange={setKept}
        hint="They may still have slow weeks, but never give it up on their own." />}
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
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const clean = name.trim()
    if (!clean) return
    const body = level >= 0 ? { name: clean, level } : { name: clean }
    if (await act(() => api<HobbiesView>('/life/hobbies', body), `Added ${clean}. They will never give it up on their own.`)) onDone()
  }
  return (
    <form className="rename-form home-add" onSubmit={(event) => void save(event)}>
      <label htmlFor="hobby-add-name">Pastime</label>
      <input id="hobby-add-name" value={name} maxLength={40} placeholder="Pottery, chess, learning Spanish" onChange={(event) => setName(event.target.value)} />
      <LevelSelect id="hobby-add-level" view={view} value={level} onChange={setLevel} unset="Picked for them" />
      <div className="rename-row">
        <button type="submit" className="button primary">Add</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

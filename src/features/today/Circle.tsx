import { useState } from 'react'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Pencil, RotateCcw, UserMinus } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, DiaryEntry } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { displayName, personFacts, personNow, personWork } from './circleText'
import { eventWhen } from './todayText'

const CIRCLE_KEY = ['circle']
const DIARY_PAGE = 20

type Act = (action: () => Promise<unknown>, done: string) => Promise<boolean>

/** The companion's supporting people (PRD T8): fictional, never the user, renamed or removed from here. */
export function Circle({ name }: { name: string }) {
  const client = useQueryClient()
  const [removed, setRemoved] = useState(false)
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const circle = useQuery({ queryKey: [...CIRCLE_KEY, removed], queryFn: () => api<CirclePerson[]>(`/life/circle?include_removed=${removed}`) })
  const act: Act = async (action, done) => {
    try {
      await action()
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    } finally {
      void client.invalidateQueries({ queryKey: CIRCLE_KEY })
      void client.invalidateQueries({ queryKey: ['today'] })
    }
  }
  return (
    <section className="today-section" aria-labelledby="circle-heading">
      <h2 id="circle-heading">People in {name}'s life</h2>
      <p className="subtle">Fictional people in {name}'s world. They are never you, and nothing about them is treated as a fact about you.</p>
      <Toggle label="Show people you removed" checked={removed} onChange={setRemoved} />
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {circle.isPending && <Loading label="Loading the people in their life" />}
      {circle.isError && <Notice tone="error">{circle.error.message}</Notice>}
      {circle.isSuccess && circle.data.length === 0 && <p className="subtle">No one yet. People appear once {name} has a home city.</p>}
      {circle.isSuccess && circle.data.length > 0 && (
        <ul className="person-list">{circle.data.map((person) => <PersonCard key={person.id} person={person} companion={name} act={act} />)}</ul>
      )}
    </section>
  )
}

function PersonCard({ person, companion, act }: { person: CirclePerson; companion: string; act: Act }) {
  const [renaming, setRenaming] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [diary, setDiary] = useState(false)
  const gone = person.status === 'removed'
  const work = personWork(person)
  const remove = async () => { setRemoving(false); await act(() => api(`/life/circle/${person.id}/remove`, {}), `${person.name} is no longer part of ${companion}'s upcoming days.`) }
  const restore = () => act(() => api(`/life/circle/${person.id}/restore`, {}), `${person.name} is back in ${companion}'s life.`)
  return (
    <li className={`person-card${gone ? ' removed' : ''}`}>
      <header>
        <h3>{displayName(person)}</h3>
        <p className="subtle">{personFacts(person)}</p>
      </header>
      {gone ? <p className="subtle">Removed. Moments that already happened still mention them.</p> : <PersonDetails person={person} work={work} />}
      {renaming && <RenameForm person={person} act={act} onDone={() => setRenaming(false)} />}
      {!renaming && (
        <div className="person-actions">
          {!gone && <button type="button" className="text-button" onClick={() => setRenaming(true)}><Pencil aria-hidden="true" />Rename</button>}
          <button type="button" className="text-button" aria-expanded={diary} onClick={() => setDiary((open) => !open)}><BookOpen aria-hidden="true" />{diary ? 'Hide diary' : 'Diary'}</button>
          {gone
            ? <button type="button" className="text-button" onClick={() => void restore()}><RotateCcw aria-hidden="true" />Restore</button>
            : <button type="button" className="text-button" onClick={() => setRemoving(true)}><UserMinus aria-hidden="true" />Remove</button>}
        </div>
      )}
      {diary && <Diary person={person} />}
      {removing && (
        <ConfirmDialog title={`Remove ${person.name}?`} onClose={() => setRemoving(false)} actions={<>
          <button type="button" className="button" onClick={() => setRemoving(false)}>Cancel</button>
          <button type="button" className="button primary" onClick={() => void remove()}>Remove</button>
        </>}>
          <p>{person.name} stops appearing in {companion}'s upcoming days. Moments that already happened keep them. You can restore them later.</p>
        </ConfirmDialog>
      )}
    </li>
  )
}

function PersonDetails({ person, work }: { person: CirclePerson; work: string | null }) {
  return <>
    <p>{personNow(person)}</p>
    {work && <p className="subtle">{work}</p>}
    {person.haunts && person.haunts.length > 0 && <p className="subtle">Often at {person.haunts.join(', ')}</p>}
    {person.recent.length > 0 && <ul className="diary-list">{person.recent.map((entry) => <DiaryLine key={entry.slot} entry={entry} />)}</ul>}
  </>
}

function RenameForm({ person, act, onDone }: { person: CirclePerson; act: Act; onDone: () => void }) {
  const [value, setValue] = useState(person.name)
  const save = async () => {
    const next = value.trim()
    if (!next || next === person.name) { onDone(); return }
    if (await act(() => api(`/life/circle/${person.id}`, { name: next }, 'PATCH'), `Renamed ${person.name} to ${next}. Moments that already happened keep the earlier name.`)) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => { event.preventDefault(); void save() }}>
      <label htmlFor={`rename-${person.id}`}>Name used in {person.name}'s moments</label>
      <div className="rename-row">
        <input id={`rename-${person.id}`} value={value} maxLength={60} onChange={(event) => setValue(event.target.value)} />
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function Diary({ person }: { person: CirclePerson }) {
  const diary = useInfiniteQuery({
    queryKey: [...CIRCLE_KEY, 'diary', person.id],
    queryFn: ({ pageParam }) => api<DiaryEntry[]>(`/life/circle/${person.id}/diary?limit=${DIARY_PAGE}${pageParam ? `&before=${encodeURIComponent(pageParam)}` : ''}`),
    initialPageParam: '',
    getNextPageParam: (last) => (last.length === DIARY_PAGE ? last[last.length - 1].starts_at : undefined),
  })
  if (diary.isPending) return <Loading label="Loading the diary" />
  if (diary.isError) return <Notice tone="error">{diary.error.message}</Notice>
  const entries = diary.data.pages.flat()
  return (
    <div className="diary">
      {entries.length === 0 ? <p className="subtle">Nothing written yet. Their days fill in as time passes.</p> : <ul className="diary-list">{entries.map((entry) => <DiaryLine key={entry.slot} entry={entry} />)}</ul>}
      {diary.hasNextPage && <button type="button" className="text-button" disabled={diary.isFetchingNextPage} onClick={() => void diary.fetchNextPage()}>Earlier entries</button>}
    </div>
  )
}

function DiaryLine({ entry }: { entry: DiaryEntry }) {
  return <li><time dateTime={entry.starts_at}>{eventWhen(entry.starts_at)}</time> {entry.entry.summary}</li>
}

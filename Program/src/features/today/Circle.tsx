import { useState } from 'react'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Pencil, RotateCcw, UserMinus, UserPlus, Users } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, CircleRoom, DiaryEntry } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { stageText } from '../memories/pairText'
import { displayName, personFacts, personNow, personTies, personWork } from './circleText'
import { eventWhen } from './todayText'
import { Acquaintances, TheirPeople } from './Network'

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
      {circle.isError && <ErrorNotice error={circle.error} />}
      {circle.isSuccess && circle.data.length === 0 && <p className="subtle">No one yet. People appear once {name} has a home city.</p>}
      {circle.isSuccess && circle.data.length > 0 && (
        <ul className="person-list">{circle.data.map((person) => <PersonCard key={person.id} person={person} companion={name} act={act} />)}</ul>
      )}
      {circle.isSuccess && <MorePeople name={name} act={act} />}
      {circle.isSuccess && <Acquaintances name={name} />}
    </section>
  )
}

/** Offered when the circle is smaller than it should be: a sociable companion, or a bigger size in Settings. */
function MorePeople({ name, act }: { name: string; act: Act }) {
  const room = useQuery({ queryKey: [...CIRCLE_KEY, 'room'], queryFn: () => api<CircleRoom>('/life/circle/room') })
  if (!room.data || room.data.people >= room.data.target) return null
  const missing = room.data.target - room.data.people
  const why = room.data.sociability === 'social' ? `${name} is the sociable type` : `Their circle size in Settings is ${room.data.target}`
  return (
    <div className="person-actions">
      <p className="subtle">{why}, so there is room for {missing} more {missing === 1 ? 'person' : 'people'}: coworkers, old and new friends, family. Nobody already here changes.</p>
      <button type="button" className="button" onClick={() => void act(() => api('/life/circle/grow', {}), `${missing === 1 ? 'Someone new is' : `${missing} new people are`} now part of ${name}'s life.`)}><UserPlus aria-hidden="true" />Add {missing === 1 ? 'one person' : `${missing} people`}</button>
    </div>
  )
}

function PersonCard({ person, companion, act }: { person: CirclePerson; companion: string; act: Act }) {
  const [renaming, setRenaming] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [diary, setDiary] = useState(false)
  const [network, setNetwork] = useState(false)
  const gone = person.status === 'removed'
  const work = personWork(person)
  const remove = async () => { setRemoving(false); await act(() => api(`/life/circle/${person.id}/remove`, {}), `${person.name} is no longer part of ${companion}'s upcoming days.`) }
  const restore = () => act(() => api(`/life/circle/${person.id}/restore`, {}), `${person.name} is back in ${companion}'s life.`)
  return (
    <li className={`person-card${gone ? ' removed' : ''}`}>
      <header>
        <h3>{displayName(person)}</h3>
        <p className="subtle">{personFacts(person)}</p>
        {person.stage && <p className="subtle pair-stage">With {companion}: {stageText(person.stage, person.name)}</p>}
      </header>
      {gone ? <p className="subtle">Removed. Moments that already happened still mention them.</p> : <PersonDetails person={person} work={work} />}
      {renaming && <RenameForm person={person} act={act} onDone={() => setRenaming(false)} />}
      {!renaming && <PersonActions gone={gone} diary={diary} network={network} onRename={() => setRenaming(true)} onDiary={() => setDiary((open) => !open)}
        onNetwork={() => setNetwork((open) => !open)} onRemove={() => setRemoving(true)} onRestore={() => void restore()} />}
      {diary && <Diary person={person} />}
      {network && !gone && <TheirPeople personKey={person.key} name={person.name} />}
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

interface ActionsProps { gone: boolean; diary: boolean; network: boolean; onRename: () => void; onDiary: () => void; onNetwork: () => void; onRemove: () => void; onRestore: () => void }

function PersonActions({ gone, diary, network, onRename, onDiary, onNetwork, onRemove, onRestore }: ActionsProps) {
  return (
    <div className="person-actions">
      {!gone && <button type="button" className="text-button" onClick={onRename}><Pencil aria-hidden="true" />Rename</button>}
      <button type="button" className="text-button" aria-expanded={diary} onClick={onDiary}><BookOpen aria-hidden="true" />{diary ? 'Hide diary' : 'Diary'}</button>
      {!gone && <button type="button" className="text-button" aria-expanded={network} onClick={onNetwork}><Users aria-hidden="true" />{network ? 'Hide their people' : 'Their people'}</button>}
      {gone
        ? <button type="button" className="text-button" onClick={onRestore}><RotateCcw aria-hidden="true" />Restore</button>
        : <button type="button" className="text-button" onClick={onRemove}><UserMinus aria-hidden="true" />Remove</button>}
    </div>
  )
}

function PersonDetails({ person, work }: { person: CirclePerson; work: string | null }) {
  return <>
    <p>{personNow(person)}</p>
    {work && <p className="subtle">{work}</p>}
    {personTies(person) && <p className="subtle">{personTies(person)}</p>}
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
  if (diary.isError) return <ErrorNotice error={diary.error} />
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

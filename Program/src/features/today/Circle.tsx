import { useState } from 'react'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, HeartHandshake, Pencil, RotateCcw, UserMinus, UserPlus, Users } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, CircleRoom, DiaryEntry } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { stageText } from '../memories/pairText'
import { displayName, metText, personFacts, personNow, personTies, personWork } from './circleText'
import { WhyItWent } from './WhyItWent'
import { eventWhen } from './todayText'
import { Acquaintances, TheirPeople } from './Network'
import { PetLines } from '../pets/PetLines'
import { childLabel, childLine, expectingLine } from '../character/familiesText'
import { lateText } from '../character/lossText'
import { useLifeSettings } from '../settings/useLifeSettings'

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
      {circle.isSuccess && circle.data.length === 0 && <p className="subtle">No one yet. People join {name}'s life as their days begin.</p>}
      {circle.isSuccess && circle.data.length > 0 && <People people={circle.data} name={name} act={act} />}
      {circle.isSuccess && <MorePeople name={name} act={act} />}
      {circle.isSuccess && <Acquaintances name={name} />}
    </section>
  )
}

/** The living first; people who passed away in a small Remembered group at the end. */
function People({ people, name, act }: { people: CirclePerson[]; name: string; act: Act }) {
  const living = people.filter((person) => !person.late)
  const late = people.filter((person) => person.late)
  return <>
    {living.length > 0 && <ul className="person-list">{living.map((person) => <PersonCard key={person.id} person={person} companion={name} act={act} />)}</ul>}
    {late.length > 0 && <>
      <h3>Remembered</h3>
      <ul className="person-list">{late.map((person) => <PersonCard key={person.id} person={person} companion={name} act={act} />)}</ul>
    </>}
  </>
}

/** The circle fills itself to its size; after people were removed, new ones can take their places. */
function MorePeople({ name, act }: { name: string; act: Act }) {
  const room = useQuery({ queryKey: [...CIRCLE_KEY, 'room'], queryFn: () => api<CircleRoom>('/life/circle/room') })
  if (!room.data || room.data.people >= room.data.target) return null
  const missing = room.data.target - room.data.people
  return (
    <div className="person-actions">
      <p className="subtle">Since you removed {missing === 1 ? 'someone' : 'some people'}, there is room for {missing} more in {name}'s life: coworkers, old and new friends, family. Nobody already here changes.</p>
      <button type="button" className="button" onClick={() => void act(() => api('/life/circle/grow', {}), `${missing === 1 ? 'Someone new is' : `${missing} new people are`} now part of ${name}'s life.`)}><UserPlus aria-hidden="true" />Add {missing === 1 ? 'one person' : `${missing} people`}</button>
    </div>
  )
}

const cardClass = (person: CirclePerson) => `person-card${person.late ? ' late' : person.status === 'removed' ? ' removed' : ''}`

function PersonCard({ person, companion, act }: { person: CirclePerson; companion: string; act: Act }) {
  const [renaming, setRenaming] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [bringing, setBringing] = useState(false)
  const [diary, setDiary] = useState(false)
  const [network, setNetwork] = useState(false)
  const late = person.late ? person.late : null
  const gone = person.status === 'removed'
  const remove = async () => { setRemoving(false); await act(() => api(`/life/circle/${person.id}/remove`, {}), `${person.name} is no longer part of ${companion}'s upcoming days.`) }
  const restore = () => act(() => api(`/life/circle/${person.id}/restore`, {}), `${person.name} is back in ${companion}'s life.`)
  const bringBack = async () => { setBringing(false); await act(() => api(`/life/circle/${person.id}/bring-back`, {}), `${person.name} is alive again, back in ${companion}'s life.`) }
  return (
    <li className={cardClass(person)}>
      <PersonHeader person={person} companion={companion} />
      <PersonState person={person} companion={companion} act={act} />
      {renaming && <RenameForm person={person} act={act} onDone={() => setRenaming(false)} />}
      {!renaming && <PersonActions gone={gone} late={!!late} diary={diary} network={network} onRename={() => setRenaming(true)} onDiary={() => setDiary((open) => !open)}
        onNetwork={() => setNetwork((open) => !open)} onRemove={() => setRemoving(true)} onRestore={() => void (late ? setBringing(true) : restore())} />}
      {bringing && <BringBack person={person} companion={companion} onClose={() => setBringing(false)} onConfirm={() => void bringBack()} />}
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

function PersonHeader({ person, companion }: { person: CirclePerson; companion: string }) {
  return (
    <header>
      <h3>{displayName(person)}</h3>
      <p className="subtle">{personFacts(person)}</p>
      {person.love && <p className="subtle pair-stage">{person.love}</p>}
      {person.stage && <p className="subtle pair-stage">With {companion}: {stageText(person.stage, person.name)}</p>}
      {person.love_odds && <WhyItWent id={person.love_odds} />}
      <MetYou person={person} />
    </header>
  )
}

/** Whether they have met you, and what they think of you (companion/life/their_people.py), with the odds under
 * Hidden values. */
function MetYou({ person }: { person: CirclePerson }) {
  const text = metText(person)
  if (!text) return null
  return <>
    <p className="subtle met-you"><HeartHandshake aria-hidden="true" />{text}</p>
    {person.met?.consequence_id && !person.met.meeting && <WhyItWent id={person.met.consequence_id} />}
  </>
}

/** What the card says about them: their days, or that they were removed or passed away. */
function PersonState({ person, companion, act }: { person: CirclePerson; companion: string; act: Act }) {
  if (person.late) return <Late person={person} died={person.late} />
  if (person.status === 'removed') return <p className="subtle">Removed. Moments that already happened still mention them.</p>
  return <>
    <PersonDetails person={person} work={personWork(person)} companion={companion} />
    <CanPassAway person={person} act={act} />
  </>
}

function BringBack({ person, companion, onClose, onConfirm }: { person: CirclePerson; companion: string; onClose: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog title={`Undo ${person.name}'s passing?`} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Keep</button>
      <button type="button" className="button primary" onClick={onConfirm}>Undo</button>
    </>}>
      <p>{person.name} is alive again from today, back in {companion}'s life. The funeral is called off and {companion} stops grieving. Moments that already happened stay as they were.</p>
    </ConfirmDialog>
  )
}

/** Someone who passed away (companion/life/loss.py): when, and how it went under Hidden values. */
function Late({ person, died }: { person: CirclePerson; died: string }) {
  return <>
    <p className="subtle">{lateText(died)} Moments that already happened still mention them.</p>
    {person.loss?.consequence_id && <WhyItWent id={person.loss.consequence_id} />}
  </>
}

/** With People can pass away on: whether this adult can. Someone written into the character starts spared. */
function CanPassAway({ person, act }: { person: CirclePerson; act: Act }) {
  const { data } = useLifeSettings()
  if (!data?.people_pass_away || (person.age ?? 0) < 18 || person.love) return null
  const spared = person.spared ?? Boolean(person.sheet)
  const save = (value: boolean) => act(() => api(`/life/circle/${person.id}/spared`, { spared: !value }),
    value ? `${person.name} can pass away, like anyone else.` : `${person.name} won't pass away.`)
  return <Toggle label="Can pass away" checked={!spared} onChange={(value) => void save(value)}
    hint={person.sheet ? 'You wrote them into the character, so they are spared unless you turn this on.' : undefined} />
}

interface ActionsProps { gone: boolean; late: boolean; diary: boolean; network: boolean; onRename: () => void; onDiary: () => void; onNetwork: () => void; onRemove: () => void; onRestore: () => void }

function PersonActions({ gone, late, diary, network, onRename, onDiary, onNetwork, onRemove, onRestore }: ActionsProps) {
  return (
    <div className="person-actions">
      {!gone && <button type="button" className="text-button" onClick={onRename}><Pencil aria-hidden="true" />Rename</button>}
      <button type="button" className="text-button" aria-expanded={diary} onClick={onDiary}><BookOpen aria-hidden="true" />{diary ? 'Hide diary' : 'Diary'}</button>
      {!gone && <button type="button" className="text-button" aria-expanded={network} onClick={onNetwork}><Users aria-hidden="true" />{network ? 'Hide their people' : 'Their people'}</button>}
      {gone
        ? <button type="button" className="text-button" onClick={onRestore}><RotateCcw aria-hidden="true" />{late ? 'Undo' : 'Restore'}</button>
        : <button type="button" className="text-button" onClick={onRemove}><UserMinus aria-hidden="true" />Remove</button>}
    </div>
  )
}

function PersonDetails({ person, work, companion }: { person: CirclePerson; work: string | null; companion: string }) {
  return <>
    <p>{personNow(person)}</p>
    {work && <p className="subtle">{work}</p>}
    {personTies(person) && <p className="subtle">{personTies(person)}</p>}
    {person.haunts && person.haunts.length > 0 && <p className="subtle">Often at {person.haunts.join(', ')}</p>}
    <ChildLines person={person} companion={companion} />
    <PetLines pets={person.pets} />
    {person.recent.length > 0 && <ul className="diary-list">{person.recent.map((entry) => <DiaryLine key={entry.slot} entry={entry} />)}</ul>}
  </>
}

/** Their children and a baby on the way (companion/life/families.py), in words only. */
function ChildLines({ person, companion }: { person: CirclePerson; companion: string }) {
  const expecting = expectingLine(person)
  return <>
    {expecting && <p className="subtle pet-line"><span className="pet-line-label">Expecting ·</span> {expecting}.</p>}
    {(person.children ?? []).map((child) => (
      <p key={child.id} className="subtle pet-line"><span className="pet-line-label">{childLabel(child)} ·</span> {childLine(child, person.name, companion)}.</p>
    ))}
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

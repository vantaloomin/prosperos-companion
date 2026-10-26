import { useEffect, useRef, useState } from 'react'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, HeartHandshake, Pencil, Plus, RotateCcw, UserMinus, UserPlus, Users } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, CircleRoom, DiaryEntry } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { stageText } from '../memories/pairText'
import { displayName, metText, personFacts, personNow, personTies, personWork } from './circleText'
import { WhyItWent } from './WhyItWent'
import { PersonForm, type Act } from './PersonForm'
import { eventWhen } from './todayText'
import { Acquaintances, TheirPeople } from './Network'
import { PetLines } from '../pets/PetLines'
import { CirclePets } from './CirclePets'
import { childLabel, childLine, expectingLabel, expectingLine } from '../character/familiesText'
import { lateText } from '../character/lossText'
import { useLifeSettings } from '../settings/useLifeSettings'
import { KindFields } from '../kinds/KindFields'
import { useKindChoices } from '../kinds/useKindChoices'
import { kindSummary } from '../kinds/kindText'

const CIRCLE_KEY = ['circle']
const DIARY_PAGE = 20

type Feedback = { tone: 'info' | 'error'; text: string }

/** The companion's supporting people (PRD T8): fictional, never the user, changed, added or removed from here. */
export function Circle({ name }: { name: string }) {
  const client = useQueryClient()
  const [removed, setRemoved] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const circle = useQuery({ queryKey: [...CIRCLE_KEY, removed], queryFn: () => api<CirclePerson[]>(`/life/circle?include_removed=${removed}`) })
  // `local` shows the outcome by the change (Iris R8) rather than at the top of the list.
  const act: Act = async (action, done, local) => {
    const tell = local ?? setFeedback
    try {
      await action()
      tell({ tone: 'info', text: done })
      return true
    } catch (error) {
      tell({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
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
      {circle.isSuccess && <CircleFooter name={name} act={act} />}
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

/** Under the list: adding someone, room for more after removals, and the people they've met through them. */
function CircleFooter({ name, act }: { name: string; act: Act }) {
  return <>
    <AddSomeone name={name} act={act} />
    <MorePeople name={name} act={act} />
    <Acquaintances name={name} />
  </>
}

/** Someone the user adds by hand, as little as a name: the app fills in the rest. The form is a card of its own;
 * focus goes to its Name, and back to the button after (Iris R7). */
function AddSomeone({ name, act }: { name: string; act: Act }) {
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useNotice()
  const button = useRef<HTMLButtonElement>(null)
  const done = () => { setAdding(false); window.setTimeout(() => button.current?.focus()) }
  return <>
    {adding
      ? <div className="person-card person-add"><PersonForm companion={name} act={act} local={setNotice} onDone={done} /></div>
      : <button ref={button} type="button" className="button person-add-button" onClick={() => { setNotice(null); setAdding(true) }}><Plus aria-hidden="true" />Add someone</button>}
    <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
  </>
}

/** A notice that fades after about six seconds (Iris R8). */
function useNotice(): [Feedback | null, (feedback: Feedback | null) => void] {
  const [notice, setNotice] = useState<Feedback | null>(null)
  useEffect(() => {
    if (!notice || notice.tone === 'error') return
    const timer = window.setTimeout(() => setNotice(null), 6000)
    return () => window.clearTimeout(timer)
  }, [notice])
  return [notice, setNotice]
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
  const [editing, setEditing] = useState(false)
  const [notice, setNotice] = useNotice()
  const edit = () => { setNotice(null); setEditing(true) }
  return (
    <li className={cardClass(person)}>
      {editing
        ? <>
          <h3>{displayName(person)}</h3>
          <PersonForm person={person} companion={companion} act={act} local={setNotice} onDone={() => setEditing(false)} />
          <CirclePets person={person} act={act} />
        </>
        : <>
          <PersonHeader person={person} companion={companion} />
          <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
          <CardBody person={person} companion={companion} act={act} onEdit={edit} />
        </>}
    </li>
  )
}

/** The card below their name: what they're up to, the actions and what those open. */
function CardBody({ person, companion, act, onEdit }: { person: CirclePerson; companion: string; act: Act; onEdit: () => void }) {
  const [removing, setRemoving] = useState(false)
  const [bringing, setBringing] = useState(false)
  const [diary, setDiary] = useState(false)
  const [network, setNetwork] = useState(false)
  const late = person.late ? person.late : null
  const gone = person.status === 'removed'
  const remove = async () => { setRemoving(false); await act(() => api(`/life/circle/${person.id}/remove`, {}), `${person.name} is no longer part of ${companion}'s upcoming days.`) }
  const restore = () => act(() => api(`/life/circle/${person.id}/restore`, {}), `${person.name} is back in ${companion}'s life.`)
  const bringBack = async () => { setBringing(false); await act(() => api(`/life/circle/${person.id}/bring-back`, {}), `${person.name} is alive again, back in ${companion}'s life.`) }
  return <>
    <PersonState person={person} companion={companion} act={act} />
    <PersonActions gone={gone} late={!!late} diary={diary} network={network} name={person.name} onEdit={onEdit} onDiary={() => setDiary((open) => !open)}
      onNetwork={() => setNetwork((open) => !open)} onRemove={() => setRemoving(true)} onRestore={() => void (late ? setBringing(true) : restore())} />
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
  </>
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
    <PersonKind person={person} act={act} />
  </>
}

/** Their kind and How long they live, folded away: the app's pick (a relative shares the companion's kind) until the
 * user picks another (companion/world/lifespans.py). */
function PersonKind({ person, act }: { person: CirclePerson; act: Act }) {
  const choices = useKindChoices()
  if (!person.kind || (person.age ?? 0) < 18) return null
  const found = person.kind.found ?? 'human'
  const label = choices?.kinds.find((item) => item.id === found)?.label ?? 'Human'
  const save = (change: { kind: string; lifespan: number | null }) => act(() => api(`/life/circle/${person.id}/kind`, change, 'PUT'),
    `Saved how ${person.name} ages. Their age stays ${person.age}.`)
  return (
    <details className="our-child-more person-kind">
      <summary>{kindSummary(person.kind)}</summary>
      <KindFields id={`person-${person.id}`} shown={person.kind} found={{ kind: found, label, source: 'app' }} picked={person.own_kind ?? ''}
        own={person.kind.own} age={person.age} choices={choices} onChange={(change) => void save(change)} />
    </details>
  )
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
  const spared = person.spared ?? Boolean(person.sheet || person.by_hand)
  const save = (value: boolean) => act(() => api(`/life/circle/${person.id}/spared`, { spared: !value }),
    value ? `${person.name} can pass away, like anyone else.` : `${person.name} won't pass away.`)
  return <Toggle label="Can pass away" checked={!spared} onChange={(value) => void save(value)}
    hint={person.sheet ? 'You wrote them into the character, so they are spared unless you turn this on.'
      : person.by_hand ? 'You added them yourself, so they are spared unless you turn this on.' : undefined} />
}

interface ActionsProps { gone: boolean; late: boolean; diary: boolean; network: boolean; name: string; onEdit: () => void; onDiary: () => void; onNetwork: () => void; onRemove: () => void; onRestore: () => void }

function PersonActions({ gone, late, diary, network, name, onEdit, onDiary, onNetwork, onRemove, onRestore }: ActionsProps) {
  return (
    <div className="person-actions">
      {!gone && <button type="button" className="text-button" aria-label={`Edit ${name}`} onClick={onEdit}><Pencil aria-hidden="true" />Edit</button>}
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
    {person.note && <PersonNote note={person.note} />}
    {personTies(person) && <p className="subtle">{personTies(person)}</p>}
    {person.haunts && person.haunts.length > 0 && <p className="subtle">Often at {person.haunts.join(', ')}</p>}
    <ChildLines person={person} companion={companion} />
    <PetLines pets={person.pets} />
    {person.recent.length > 0 && <ul className="diary-list">{person.recent.map((entry) => <DiaryLine key={entry.slot} entry={entry} />)}</ul>}
  </>
}

/** The user's own words about them, in the regular text color, clamped with More (Iris R6, S2). */
function PersonNote({ note }: { note: string }) {
  const [open, setOpen] = useState(false)
  const long = note.length > 140
  return <div className="person-note-block">
    <p className={`person-note${long && !open ? ' clamped' : ''}`}>{note}</p>
    {long && <button type="button" className="text-button person-note-more" aria-expanded={open} onClick={() => setOpen((value) => !value)}>{open ? 'Less' : 'More'}</button>}
  </div>
}

/** Their children and a baby on the way (companion/life/families.py), in words only. */
function ChildLines({ person, companion }: { person: CirclePerson; companion: string }) {
  const expecting = expectingLine(person)
  return <>
    {expecting && <p className="subtle pet-line"><span className="pet-line-label">{expectingLabel(person)} ·</span> {expecting}.</p>}
    {(person.children ?? []).map((child) => (
      <p key={child.id} className="subtle pet-line"><span className="pet-line-label">{childLabel(child)} ·</span> {childLine(child, person.name, companion)}.</p>
    ))}
  </>
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

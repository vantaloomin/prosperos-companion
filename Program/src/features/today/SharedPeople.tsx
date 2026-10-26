import { useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, ChevronDown, Pencil, UserMinus, UsersRound } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, ShareablePerson } from '../../types'
import { Notice } from '../../components/Feedback'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { RELATION_WORDS, displayName, fromText, personFacts, personNow, personWork } from './circleText'
import { useCircleHome } from './useCircleHome'
import type { Act } from './PersonForm'

type Feedback = { tone: 'info' | 'error'; text: string }

/** Someone from another companion's circle: the same person, changed on their own companion's page. Here the user
 * changes only who they are to this companion, or takes them out of this companion's life. */
export function SharedCard({ person, companion, act, diary }: { person: CirclePerson; companion: string; act: Act; diary: () => ReactNode }) {
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [showDiary, setShowDiary] = useState(false)
  const [notice, setNotice] = useState<Feedback | null>(null)
  const owner = person.shared?.owner ?? ''
  const remove = async () => {
    setRemoving(false)
    await act(() => api(`/life/circle/shared/${person.id}/remove`, {}), `${person.name} is no longer part of ${companion}'s life. They stay in ${owner}'s.`)
  }
  return (
    <li className="person-card">
      <header>
        <h3>{displayName(person)}</h3>
        <p className="subtle">{personFacts(person)}</p>
        <p className="subtle person-from"><UsersRound aria-hidden="true" />{fromText(person)}</p>
      </header>
      <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
      {editing
        ? <RoleForm person={person} companion={companion} act={act} local={setNotice} onDone={() => setEditing(false)} />
        : <SharedDetails person={person} />}
      {!editing && <div className="person-actions">
        <button type="button" className="text-button" aria-label={`Edit who ${person.name} is to ${companion}`} onClick={() => { setNotice(null); setEditing(true) }}><Pencil aria-hidden="true" />Edit</button>
        <button type="button" className="text-button" aria-expanded={showDiary} onClick={() => setShowDiary((open) => !open)}><BookOpen aria-hidden="true" />{showDiary ? 'Hide diary' : 'Diary'}</button>
        <button type="button" className="text-button" onClick={() => setRemoving(true)}><UserMinus aria-hidden="true" />Remove</button>
      </div>}
      {showDiary && diary()}
      {removing && (
        <ConfirmDialog title={`Remove ${person.name} from ${companion}'s life?`} onClose={() => setRemoving(false)} actions={<>
          <button type="button" className="button" onClick={() => setRemoving(false)}>Cancel</button>
          <button type="button" className="button primary" onClick={() => void remove()}>Remove</button>
        </>}>
          <p>{companion} stops knowing {person.name}. {person.name} stays in {owner}'s life as they are. You can add them again later.</p>
        </ConfirmDialog>
      )}
    </li>
  )
}

function SharedDetails({ person }: { person: CirclePerson }) {
  const aboard = useCircleHome()
  const work = personWork(person)
  return <>
    <p>{personNow(person, aboard)}</p>
    {work && <p className="subtle">{work}</p>}
    {person.note && <p className="person-note">{person.note}</p>}
    <p className="subtle">To change who they are, open {person.shared?.owner}'s page.</p>
  </>
}

/** Who they are to this companion: the one thing changed from here. */
function RoleForm({ person, companion, act, local, onDone }: { person: CirclePerson; companion: string; act: Act; local: (feedback: Feedback) => void; onDone: () => void }) {
  const [role, setRole] = useState(person.role)
  const id = `shared-role-${person.id}`
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (role.trim() === person.role) { onDone(); return }
    if (await act(() => api(`/life/circle/shared/${person.id}`, { role: role.trim() }, 'PUT'), `Saved. ${person.name} is ${companion}'s ${role.trim().toLowerCase()}.`, local)) onDone()
  }
  return (
    <form className="circle-form" onSubmit={(event) => void submit(event)} aria-label={`Who ${person.name} is to ${companion}`}>
      <RoleField id={id} companion={companion} value={role} onChange={setRole} />
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function RoleField({ id, companion, value, onChange, required = true }: { id: string; companion: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return (
    <div className="circle-field">
      <label htmlFor={id}>Who they are to {companion}</label>
      <span className="suggest">
        <input id={id} value={value} list={`${id}-list`} maxLength={40} required={required} placeholder="Friend" autoComplete="off" onChange={(event) => onChange(event.target.value)} />
        <ChevronDown aria-hidden="true" />
        <datalist id={`${id}-list`}>{RELATION_WORDS.map((option) => <option key={option} value={option} />)}</datalist>
      </span>
    </div>
  )
}

/** Adding someone another companion already knows, such as Sarek's wife as Spock's mother: shown only when the
 * other companions have people to offer. Focus goes to the picker, and back to the button after (Iris R7). */
export function AddShared({ companion, act }: { companion: string; act: Act }) {
  const offered = useQuery({ queryKey: ['circle', 'shareable'], queryFn: () => api<ShareablePerson[]>('/life/circle/shareable') })
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useState<Feedback | null>(null)
  const button = useRef<HTMLButtonElement>(null)
  if (!offered.data?.length && !adding) return notice ? <div aria-live="polite"><Notice tone={notice.tone}>{notice.text}</Notice></div> : null
  const done = () => { setAdding(false); window.setTimeout(() => button.current?.focus()) }
  return <>
    {adding
      ? <div className="person-card person-add"><SharedForm people={offered.data ?? []} companion={companion} act={act} local={setNotice} onDone={done} /></div>
      : <button ref={button} type="button" className="button person-add-button" onClick={() => { setNotice(null); setAdding(true) }}><UsersRound aria-hidden="true" />Add someone another companion knows</button>}
    <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
  </>
}

/** The people on offer, grouped by whose life they are in, and who they are to this companion. */
function SharedForm({ people, companion, act, local, onDone }: { people: ShareablePerson[]; companion: string; act: Act; local: (feedback: Feedback) => void; onDone: () => void }) {
  const [picked, setPicked] = useState('')
  const [role, setRole] = useState('')
  const owners = [...new Map(people.map((person) => [person.owner_id, person.owner])).entries()]
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const person = people.find((item) => item.id === picked)
    if (!person) return
    const as = role.trim() || 'friend'
    if (await act(() => api('/life/circle/shared', { person_id: person.id, role: as }), `${person.name} is now part of ${companion}'s life too, as their ${as.toLowerCase()}. They stay in ${person.owner}'s.`, local)) onDone()
  }
  return (
    <form className="circle-form" onSubmit={(event) => void submit(event)} aria-label={`Add someone another companion knows to ${companion}'s life`}>
      <p className="subtle">The same person, in both lives. Their days, job and diary stay with the companion they came from.</p>
      <div className="circle-field">
        <label htmlFor="shared-person">Who</label>
        <select id="shared-person" value={picked} required autoFocus onChange={(event) => setPicked(event.target.value)}>
          <option value="" disabled>Pick someone</option>
          {owners.map(([ownerId, owner]) => (
            <optgroup key={ownerId} label={`${owner}'s life`}>
              {people.filter((person) => person.owner_id === ownerId).map((person) => <option key={person.id} value={person.id}>{person.full_name} ({owner}'s {person.role})</option>)}
            </optgroup>
          ))}
        </select>
      </div>
      <RoleField id="shared-role-new" companion={companion} value={role} onChange={setRole} required={false} />
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Add to {companion}'s life</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ListChecks, Pencil, Pin, Plus, Trash2, UserPlus } from 'lucide-react'
import { api } from '../../api'
import type { Memory, Message, Person } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { MemoryCard, type MemoryActions } from './MemoryCard'
import { PEOPLE_KEY, groupPeople, personLine } from './memoryGroups'

type Run = <T>(action: () => Promise<T>, done: string) => Promise<T | null>

/** The people in your life the companion has heard about, one card each with what you told them. */
export function People({ name, all, sources, actions, run }: { name: string; all: Memory[]; sources: Map<string, Message>; actions: MemoryActions; run: Run }) {
  const people = useQuery({ queryKey: [...PEOPLE_KEY, all.length], queryFn: () => api<Person[]>('/people') })
  const [adding, setAdding] = useState(false)
  const groups = groupPeople(people.data ?? [], all)
  return (
    <section className="memory-group people" aria-labelledby="people-heading">
      <div className="people-header">
        <h2 id="people-heading">People in your life</h2>
        {!adding && <button type="button" className="text-button" onClick={() => setAdding(true)}><UserPlus aria-hidden="true" />Add someone</button>}
      </div>
      <p className="subtle">Who you've mentioned and what you said about them. {name} has never met them, only knows what you told them, and may now and then ask how they are.</p>
      {adding && <PersonForm submit="Add" onCancel={() => setAdding(false)} onSave={async (body) => {
        const saved = await run(() => api<Person>('/people', body), `${name} will remember ${body.name || `your ${body.relation}`}.`)
        if (saved) setAdding(false)
      }} />}
      {groups.length === 0 && !adding && <p className="subtle">No one yet. With automatic memory on, people you mention by name or as “my sister”, “my boss” are added here.</p>}
      {groups.length > 0 && <ul className="person-list">
        {groups.map(({ person, current }) => <PersonCard key={person.id} person={person} memories={current} name={name} all={all} sources={sources} actions={actions} run={run} />)}
      </ul>}
    </section>
  )
}

const topicOf = (memory: Memory) => memory.subject_key?.split('.').pop() ?? ''
/** What the card shows: current values only; replaced ones stay in Edit details. */
const shown = (memory: Memory) => memory.current !== false && memory.status !== 'superseded'
const who = (person: Person) => person.name ?? `your ${person.relation}`

/** What you can tell about someone, matching what is learned from chat. Work and studies make no sense for a pet.
 * `one` marks a topic with one value at a time, `line` a one-line box, `card` the label on the card. */
interface Detail { topic: string; label: string; card: string; placeholder: string; pet?: string; pets: boolean; one?: string; line?: boolean }
const DETAILS: Detail[] = [
  { topic: 'about', label: 'About them', card: 'About them', placeholder: 'Anything: what they are like, how you met, what matters to them…', pet: 'What they are like, where they came from…', pets: true },
  { topic: 'work', label: 'Work', card: 'Work', placeholder: 'nurse at St. Mary’s', pets: false, one: 'work', line: true },
  { topic: 'home_city', label: 'Where they live', card: 'Lives in', placeholder: 'Cork', pets: false, one: 'where they live', line: true },
  { topic: 'age', label: 'Age', card: 'Age', placeholder: '34', pet: '4', pets: true, one: 'age', line: true },
  { topic: 'birthday', label: 'Birthday', card: 'Birthday', placeholder: 'March 3', pets: true, one: 'birthday', line: true },
  { topic: 'studies', label: 'Studies', card: 'Studies', placeholder: 'law at Trinity', pets: false },
  { topic: 'has', label: 'Family or pets', card: 'Family or pets', placeholder: 'two kids, a dog called Rex', pets: false },
  { topic: 'likes', label: 'Likes', card: 'Likes', placeholder: 'climbing, old films', pet: 'tuna, the sunny windowsill', pets: true },
  { topic: 'dislikes', label: 'Dislikes', card: 'Dislikes', placeholder: 'early mornings, crowds', pet: 'the vet, thunder', pets: true },
  { topic: 'news', label: 'News', card: 'News', placeholder: 'just got engaged', pet: 'had a check-up, all fine', pets: true },
]
/** The card's compact lines, in this order; About them and Age sit above them. */
const LINE_ORDER = ['work', 'home_city', 'birthday', 'studies', 'has', 'likes', 'dislikes', 'news']
const detailFor = (topic: string) => DETAILS.find((detail) => detail.topic === topic)

type Mode = 'view' | 'edit' | 'rename' | 'add'

function PersonCard({ person, memories, name, all, sources, actions, run }: { person: Person; memories: Memory[]; name: string; all: Memory[]; sources: Map<string, Message>; actions: MemoryActions; run: Run }) {
  const [mode, setMode] = useState<Mode>('view')
  const [forgetting, setForgetting] = useState(false)
  const facts = memories.filter((memory) => shown(memory) && topicOf(memory) !== 'who')
  const age = facts.find((memory) => topicOf(memory) === 'age' && memory.status !== 'excluded')
  const current = Object.fromEntries(facts.map((memory) => [topicOf(memory), memory.value]))
  const headingId = `person-${person.id}`
  return (
    <li className="person-card user-person">
      <header className="user-person-header">
        <div>
          <h3 id={headingId}>{person.label}</h3>
          <p className="subtle">{personLine(person)}{age ? ` · ${age.value}` : ''}</p>
        </div>
        {mode === 'edit' && <button type="button" className="text-button" onClick={() => setMode('view')}>Done</button>}
      </header>
      {mode === 'rename' && <PersonForm person={person} submit="Save" onCancel={() => setMode('view')} onSave={async (body) => {
        const saved = await run(() => api<Person>(`/people/${person.id}`, body, 'PUT'), `Saved. Everything about ${body.name || `your ${body.relation}`} uses the new name.`)
        if (saved) setMode('view')
      }} />}
      {mode === 'edit'
        ? <ul className="memory-list">{memories.map((memory) => <MemoryCard key={memory.id} memory={{ ...memory, subject: detailFor(topicOf(memory))?.label ?? memory.subject }} all={all} sources={sources} actions={actions} />)}</ul>
        : <Facts person={person} facts={facts} name={name} />}
      {mode === 'add' && <AddDetail person={person} name={name} current={current} run={run} onClose={() => setMode('view')} />}
      {(mode === 'view' || mode === 'edit') && <Actions person={person} name={name} editing={mode === 'edit'} setMode={setMode} onForget={() => setForgetting(true)} />}
      {forgetting && (
        <ConfirmDialog title={`Forget ${person.label}?`} onClose={() => setForgetting(false)} actions={<>
          <button type="button" className="button" onClick={() => setForgetting(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={() => void run(() => api(`/people/${person.id}/delete`, {}), `${person.label} and everything you said about them were forgotten.`).then(() => setForgetting(false))}>Forget</button>
        </>}>
          <p>This deletes {person.memory_ids.length === 1 ? 'the memory' : `all ${person.memory_ids.length} memories`} about {person.label}, the same way Delete does for one memory. Your messages stay in the conversation.</p>
        </ConfirmDialog>
      )}
    </li>
  )
}

/** The card's verbs in one row, like the circle cards; the add button's label says who it is about. */
function Actions({ person, name, editing, setMode, onForget }: { person: Person; name: string; editing: boolean; setMode: (mode: Mode) => void; onForget: () => void }) {
  return (
    <div className="person-actions" role="group" aria-label={`Actions for ${person.label}`}>
      <button type="button" className="text-button" aria-label={`Tell ${name} more about ${who(person)}`} onClick={() => setMode('add')}><Plus aria-hidden="true" />Tell {name} more</button>
      {!editing && <button type="button" className="text-button" onClick={() => setMode('edit')}><ListChecks aria-hidden="true" />Edit details</button>}
      <button type="button" className="text-button" onClick={() => setMode('rename')}><Pencil aria-hidden="true" />Rename</button>
      <button type="button" className="text-button danger-text" onClick={onForget}><Trash2 aria-hidden="true" />Forget</button>
    </div>
  )
}

/** About them notes as body text, then one "Label · value" line per topic, the way circle cards show theirs. */
function Facts({ person, facts, name }: { person: Person; facts: Memory[]; name: string }) {
  const notes = facts.filter((memory) => topicOf(memory) === 'about')
  const lines = facts.filter((memory) => !['about', 'age'].includes(topicOf(memory)))
    .sort((a, b) => order(a) - order(b) || a.stated_at.localeCompare(b.stated_at))
  if (!facts.length) return <p className="subtle">{onlyKnows(person, name)}</p>
  return <>
    {notes.map((memory) => <Note key={memory.id} memory={memory} />)}
    {lines.map((memory) => (
      <p key={memory.id} className={`subtle pet-line${memory.status === 'excluded' ? ' not-used' : ''}`}>
        <span className="pet-line-label">{detailFor(topicOf(memory))?.card ?? topicOf(memory)} ·</span> {memory.value}<Flags memory={memory} />
      </p>
    ))}
  </>
}

const order = (memory: Memory) => { const at = LINE_ORDER.indexOf(topicOf(memory)); return at < 0 ? LINE_ORDER.length : at }

function onlyKnows(person: Person, name: string) {
  if (person.name && person.relation) return `${name} only knows ${person.name} is your ${person.relation}.`
  if (person.name) return `${name} only knows their name.`
  return `${name} only knows you have a ${person.relation}.`
}

function Flags({ memory }: { memory: Memory }) {
  return <>
    {memory.pinned && <Pin className="user-person-pin" aria-label="Pinned" />}
    {memory.status === 'excluded' && <span> (not used)</span>}
  </>
}

function Note({ memory }: { memory: Memory }) {
  const [open, setOpen] = useState(false)
  const long = memory.value.length > 220
  return <div className={`person-note-block${memory.status === 'excluded' ? ' not-used' : ''}`}>
    <p className={`person-note${long && !open ? ' clamped' : ''}`}>{memory.value}<Flags memory={memory} /></p>
    {long && <button type="button" className="text-button person-note-more" aria-expanded={open} onClick={() => setOpen((value) => !value)}>{open ? 'Less' : 'More'}</button>}
  </div>
}

/** Tell the companion more about someone: kept as a memory about them, so Correct, Pin and Delete work on it. */
function AddDetail({ person, name, current, run, onClose }: { person: Person; name: string; current: Record<string, string>; run: Run; onClose: () => void }) {
  const [topic, setTopic] = useState('about')
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)
  const form = useRef<HTMLFormElement>(null)
  useEffect(() => { form.current?.querySelector<HTMLElement>('textarea, input')?.focus() }, [])
  const choices = DETAILS.filter((detail) => detail.pets || !person.pet)
  const picked = choices.find((detail) => detail.topic === topic) ?? choices[0]
  const placeholder = person.pet && picked.pet ? picked.pet : picked.placeholder
  const before = picked.one ? current[picked.topic] : undefined
  const hint = before ? `Replaces “${before}” (what you said before stays in history).` : undefined
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim()) return
    setSaving(true)
    const saved = await run(() => api(`/people/${person.id}/facts`, { topic: picked.topic, value: value.trim() }), `${name} will remember that about ${person.label}.`)
    setSaving(false)
    if (saved) onClose()
  }
  return (
    <form ref={form} className="person-detail-form form-stack" aria-label={`Tell ${name} more about ${who(person)}`} onSubmit={save}>
      <Field label="What it's about">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={picked.topic} onChange={(event) => setTopic(event.target.value)}>
          {choices.map((detail) => <option key={detail.topic} value={detail.topic}>{detail.label}</option>)}
        </select>
      )}</Field>
      {picked.line
        ? <TextInput label="What you know" value={value} onChange={setValue} maxLength={300} placeholder={placeholder} hint={hint} />
        : <TextArea label="What you know" value={value} onChange={setValue} maxLength={300} grows placeholder={placeholder} hint={hint} />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !value.trim()}>Add</button>
        <button type="button" className="button" onClick={onClose}>Cancel</button>
      </div>
    </form>
  )
}

function PersonForm({ person, submit, onSave, onCancel }: { person?: Person; submit: string; onSave: (body: { name: string; relation: string }) => Promise<void>; onCancel: () => void }) {
  const [name, setName] = useState(person?.name ?? '')
  const [relation, setRelation] = useState(person?.relation ?? '')
  const [saving, setSaving] = useState(false)
  const ready = !!(name.trim() || relation.trim())
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!ready) return
    setSaving(true)
    await onSave({ name: name.trim(), relation: relation.trim() })
    setSaving(false)
  }
  return (
    <form className="person-form form-stack" onSubmit={save}>
      <TextInput label="Name" value={name} onChange={setName} maxLength={80} hint="However you refer to them, such as Jo or Mum." />
      <TextInput label="How they're related to you" value={relation} onChange={setRelation} maxLength={40} placeholder="sister, best friend, boss, dog…" hint="Helps them follow who you mean when you say my sister." />
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !ready}>{submit}</button>
        <button type="button" className="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

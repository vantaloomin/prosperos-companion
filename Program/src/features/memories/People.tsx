import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Pencil, Plus, Trash2, UserPlus } from 'lucide-react'
import { api } from '../../api'
import type { Memory, Message, Person } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { MemoryCard, type MemoryActions } from './MemoryCard'
import { PEOPLE_KEY, groupPeople, personLine } from './memoryGroups'

type Run = <T>(action: () => Promise<T>, done: string) => Promise<T | null>

/** The people in your life the companion has heard about, each with what you told them. */
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
      {groups.map(({ person, current }) => (
        <section key={person.id} className="person" aria-labelledby={`person-${person.id}`}>
          <PersonHeading person={person} run={run} />
          <ul className="memory-list">
            {current.map((memory) => <MemoryCard key={memory.id} memory={memory} all={all} sources={sources} actions={actions} />)}
          </ul>
          <AddDetail person={person} name={name} run={run} />
        </section>
      ))}
    </section>
  )
}

function PersonHeading({ person, run }: { person: Person; run: Run }) {
  const [editing, setEditing] = useState(false)
  const [forgetting, setForgetting] = useState(false)
  if (editing) {
    return <PersonForm person={person} submit="Save" onCancel={() => setEditing(false)} onSave={async (body) => {
      const saved = await run(() => api<Person>(`/people/${person.id}`, body, 'PUT'), `Saved. Everything about ${body.name || `your ${body.relation}`} uses the new name.`)
      if (saved) setEditing(false)
    }} />
  }
  return (
    <div className="person-heading">
      <h3 id={`person-${person.id}`}>{person.label} <small className="subtle">{personLine(person)}</small></h3>
      <div className="memory-actions" role="group" aria-label={`Actions for ${person.label}`}>
        <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Rename</button>
        <button type="button" className="text-button danger-text" onClick={() => setForgetting(true)}><Trash2 aria-hidden="true" />Forget</button>
      </div>
      {forgetting && (
        <ConfirmDialog title={`Forget ${person.label}?`} onClose={() => setForgetting(false)} actions={<>
          <button type="button" className="button" onClick={() => setForgetting(false)}>Cancel</button>
          <button type="button" className="button danger" onClick={() => void run(() => api(`/people/${person.id}/delete`, {}), `${person.label} and everything you said about them were forgotten.`).then(() => setForgetting(false))}>Forget</button>
        </>}>
          <p>This deletes {person.memory_ids.length === 1 ? 'the memory' : `all ${person.memory_ids.length} memories`} about {person.label}, the same way Delete does for one memory. Your messages stay in the conversation.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

/** What you can tell about someone, matching what is learned from chat. Work and studies make no sense for a pet. */
const DETAILS: { topic: string; label: string; placeholder: string; pets: boolean; one?: string }[] = [
  { topic: 'about', label: 'About them', placeholder: 'Anything: what they are like, how you met, what matters to them…', pets: true },
  { topic: 'work', label: 'Work', placeholder: 'nurse at St. Mary’s', pets: false, one: 'work' },
  { topic: 'home_city', label: 'Where they live', placeholder: 'Cork', pets: false, one: 'home' },
  { topic: 'age', label: 'Age', placeholder: '34', pets: true, one: 'age' },
  { topic: 'birthday', label: 'Birthday', placeholder: 'March 3', pets: true, one: 'birthday' },
  { topic: 'studies', label: 'Studies', placeholder: 'law at Trinity', pets: false },
  { topic: 'has', label: 'Family or pets', placeholder: 'two kids, a dog called Rex', pets: false },
  { topic: 'likes', label: 'Likes', placeholder: 'climbing, old films', pets: true },
  { topic: 'dislikes', label: 'Dislikes', placeholder: 'the vet, thunder', pets: true },
  { topic: 'news', label: 'News', placeholder: 'just got engaged', pets: true },
]

/** Tell the companion more about someone: kept as a memory about them, so Correct, Pin and Delete work on it. */
function AddDetail({ person, name, run }: { person: Person; name: string; run: Run }) {
  const [open, setOpen] = useState(false)
  const [topic, setTopic] = useState('about')
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)
  const choices = DETAILS.filter((detail) => detail.pets || !person.pet)
  const picked = choices.find((detail) => detail.topic === topic) ?? choices[0]
  if (!open) {
    return <button type="button" className="text-button person-add-detail" onClick={() => setOpen(true)}><Plus aria-hidden="true" />Tell {name} more about {person.name ?? `your ${person.relation}`}</button>
  }
  const close = () => { setOpen(false); setValue(''); setTopic('about') }
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim()) return
    setSaving(true)
    const saved = await run(() => api(`/people/${person.id}/facts`, { topic: picked.topic, value: value.trim() }), `${name} will remember that about ${person.label}.`)
    setSaving(false)
    if (saved) close()
  }
  return (
    <form className="person-form form-stack" onSubmit={save}>
      <Field label="What it's about">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={picked.topic} onChange={(event) => setTopic(event.target.value)}>
          {choices.map((detail) => <option key={detail.topic} value={detail.topic}>{detail.label}</option>)}
        </select>
      )}</Field>
      <TextArea label="What you know" value={value} onChange={setValue} maxLength={300} grows placeholder={picked.placeholder}
        hint={picked.one ? `Replaces the ${picked.one} you gave before, which stays as history.` : null} />
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={saving || !value.trim()}>Add</button>
        <button type="button" className="button" onClick={close}>Cancel</button>
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

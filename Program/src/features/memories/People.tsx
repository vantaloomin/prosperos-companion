import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Pencil, Trash2, UserPlus } from 'lucide-react'
import { api } from '../../api'
import type { Memory, Message, Person } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { TextInput } from '../../components/Fields'
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

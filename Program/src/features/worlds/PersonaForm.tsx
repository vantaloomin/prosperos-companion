import { useState } from 'react'
import { api } from '../../api'
import type { Persona, PersonaGender, Worlds } from '../../types'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { GENDERS } from './worldsText'

const BIRTHDAY = /^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$/

/** Who the user is right now. Everything is optional: companions only know what is written here. */
export function PersonaForm({ persona, onSaved }: { persona: Persona; onSaved: (data: Worlds) => void }) {
  const [draft, setDraft] = useState({ name: persona.name, gender: persona.gender, age: persona.age ? String(persona.age) : '', about: persona.about, birthday: persona.birthday })
  const [note, setNote] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const set = (change: Partial<typeof draft>) => { setDraft((old) => ({ ...old, ...change })); setNote(null) }
  const age = draft.age ? Number(draft.age) : null
  const valid = (age === null || (age >= 18 && age <= 120)) && BIRTHDAY.test(draft.birthday)
  const save = async () => {
    try {
      onSaved(await api<Worlds>(`/worlds/personas/${persona.id}`, { ...draft, age }, 'PATCH'))
      setNote({ tone: 'info', text: 'Saved. Your companions know you this way from the next message.' })
    } catch (failure) { setNote({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) }
  }
  return (
    <form className="settings-section form-stack persona-form" aria-labelledby="persona-heading" onSubmit={(event) => { event.preventDefault(); if (valid) void save() }}>
      <div>
        <h2 id="persona-heading">Who you are here</h2>
        <p className="subtle">Your companions in this persona&apos;s worlds know you by this. Leave anything blank to keep it to yourself.</p>
      </div>
      <TextInput label="Name" value={draft.name} maxLength={80} onChange={(name) => set({ name })} />
      <Field label="Gender">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={draft.gender} onChange={(event) => set({ gender: event.target.value as PersonaGender })}>
          {GENDERS.map(([value, label]) => <option key={value || 'none'} value={value}>{label}</option>)}
        </select>
      )}</Field>
      <TextInput label="Age" type="number" value={draft.age} onChange={(value) => set({ age: value })} hint={age !== null && age < 18 ? 'You must be 18 or older.' : undefined} />
      <TextInput label="Birthday" value={draft.birthday} placeholder="MM-DD" maxLength={5} onChange={(birthday) => set({ birthday })}
        hint="Month and day, like 04-23. Companions remember it and wish you a happy birthday." />
      <TextArea label="About you" value={draft.about} rows={3} maxLength={2000} onChange={(about) => set({ about })}
        placeholder="Works nights as a paramedic, has a one-eyed cat called Biscuit." />
      <div className="form-actions"><button type="submit" className="button primary" disabled={!valid}>Save</button></div>
      {note && <Notice tone={note.tone}>{note.text}</Notice>}
    </form>
  )
}

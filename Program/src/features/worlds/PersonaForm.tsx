import { useState } from 'react'
import { api } from '../../api'
import type { Persona, PersonaGender, Worlds } from '../../types'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { GENDERS } from './worldsText'
import { CityPick } from './CityPick'

const BIRTHDAY = /^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$/

type Draft = { name: string; gender: PersonaGender; age: string; about: string; birthday: string }

function draftOf(persona?: Persona): Draft {
  if (!persona) return { name: '', gender: '', age: '', about: '', birthday: '' }
  return { name: persona.name, gender: persona.gender, age: persona.age ? String(persona.age) : '', about: persona.about, birthday: persona.birthday }
}

/** A new persona needs the name the user gives it; everything else may stay blank. */
function validDraft(draft: Draft, age: number | null, isNew: boolean): boolean {
  return (age === null || (age >= 18 && age <= 120)) && BIRTHDAY.test(draft.birthday) && (!isNew || !!draft.name.trim())
}

const TEXT = {
  existing: { id: 'persona-heading', heading: 'Who you are here', button: 'Save', busy: 'Saving…', intro: 'Your companions in this persona\'s worlds know you by this.' },
  new: { id: 'new-persona-heading', heading: 'A new persona', button: 'Make this persona', busy: 'Making their world…', intro: 'Who will you be? They get a world of their own, with new people in it and a first companion to meet.' },
}

/** A new persona, with their world in `city`, or the changes to one; a new one's form closes once it is made. */
async function savePersona(persona: Persona | undefined, body: Omit<Draft, 'age'> & { age: number | null }, city: string): Promise<Worlds | undefined> {
  if (!persona) { await api('/worlds/personas', { ...body, city_id: city }); return undefined }
  return api<Worlds>(`/worlds/personas/${persona.id}`, body, 'PATCH')
}

/** `cityId` is the city the user is in now, where a new persona's world is unless they pick another. */
interface PersonaFormProps { persona?: Persona; cityId: string; onSaved: (data?: Worlds) => void; onCancel?: () => void }

/** Who the user is: the one in use, or (without `persona`) a new one. Only the user says this; companions know
 * only what is written here, and nothing left blank is made up. */
export function PersonaForm({ persona, cityId, onSaved, onCancel }: PersonaFormProps) {
  const [draft, setDraft] = useState(() => draftOf(persona))
  const [city, setCity] = useState(cityId)
  const [saving, setSaving] = useState(false)
  const text = persona ? TEXT.existing : TEXT.new
  const headingId = text.id
  const [note, setNote] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const set = (change: Partial<typeof draft>) => { setDraft((old) => ({ ...old, ...change })); setNote(null) }
  const age = draft.age ? Number(draft.age) : null
  const valid = validDraft(draft, age, !persona)
  const save = async () => {
    setSaving(true)
    try {
      onSaved(await savePersona(persona, { ...draft, age }, city))
      setNote({ tone: 'info', text: 'Saved. Your companions know you this way from the next message.' })
    } catch (failure) { setNote({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) } finally { setSaving(false) }
  }
  return (
    <form className="settings-section form-stack persona-form" aria-labelledby={headingId} onSubmit={(event) => { event.preventDefault(); if (valid) void save() }}>
      <div>
        <h2 id={headingId}>{text.heading}</h2>
        <p className="subtle">{text.intro} Leave anything but the name blank to keep it to yourself.</p>
      </div>
      <TextInput label="Name" value={draft.name} maxLength={80} required={!persona} onChange={(name) => set({ name })} />
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
      {!persona && <CityPick value={city} currentId={cityId} onChange={setCity} />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={!valid || saving}>{saving ? text.busy : text.button}</button>
        {onCancel && <button type="button" className="text-button" onClick={onCancel}>Cancel</button>}
      </div>
      {note && <Notice tone={note.tone}>{note.text}</Notice>}
    </form>
  )
}

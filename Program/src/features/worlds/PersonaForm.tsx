import { useState } from 'react'
import { api } from '../../api'
import type { Persona, PersonaGender, Worlds } from '../../types'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { GENDERS } from './worldsText'
import { CityPick, SOMEWHERE_NEW } from './CityPick'
import { PersonaPets } from './PersonaPets'
import { petDrafts, petsBody, type PetDraft } from './personaPetsText'

const BIRTHDAY = /^(?:(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))?$/

type Draft = { name: string; gender: PersonaGender; age: string; about: string; birthday: string; pets: PetDraft[] }

function draftOf(persona?: Persona): Draft {
  if (!persona) return { name: '', gender: '', age: '', about: '', birthday: '', pets: [] }
  return { name: persona.name, gender: persona.gender, age: persona.age ? String(persona.age) : '', about: persona.about, birthday: persona.birthday, pets: petDrafts(persona.pets) }
}

/** A new persona needs the name the user gives it; everything else may stay blank. */
function validDraft(draft: Draft, age: number | null, isNew: boolean): boolean {
  return (age === null || (age >= 18 && age <= 120)) && BIRTHDAY.test(draft.birthday) && (!isNew || !!draft.name.trim())
}

const TEXT = {
  existing: { id: 'persona-heading', heading: 'Who you are here', button: 'Save', busy: 'Saving…', intro: 'Your companions in this persona\'s worlds know you by this.' },
  new: { id: 'new-persona-heading', heading: 'A new persona', button: 'Make this persona', busy: 'Making their world…', intro: 'Who will you be? They get a world of their own with new people in it, and you make the first companion there.' },
}

/** A new persona, with their world in `city`, or the changes to one; a new one's form closes once it is made. */
async function savePersona(persona: Persona | undefined, body: Omit<Draft, 'age' | 'pets'> & { age: number | null; pets: ReturnType<typeof petsBody> }, city: string): Promise<Worlds | undefined> {
  if (!persona) { await api('/worlds/personas', { ...body, city_id: city }); return undefined }
  return api<Worlds>(`/worlds/personas/${persona.id}`, body, 'PATCH')
}

/** `cityId` is the city the user is in now, listed in a new persona's city picker even before the cities load. */
interface PersonaFormProps { persona?: Persona; cityId: string; onSaved: (data?: Worlds) => void; onCancel?: () => void }

/** Who the user is: the one in use, or (without `persona`) a new one. Only the user says this; companions know
 * only what is written here, and nothing left blank is made up. */
export function PersonaForm({ persona, cityId, onSaved, onCancel }: PersonaFormProps) {
  const [draft, setDraft] = useState(() => draftOf(persona))
  const [city, setCity] = useState(SOMEWHERE_NEW)
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
      onSaved(await savePersona(persona, { ...draft, age, pets: petsBody(draft.pets) }, city))
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
        placeholder="Works nights as a paramedic, loves old films." />
      <PersonaPets drafts={draft.pets} onChange={(pets) => set({ pets })} persona={persona} />
      {!persona && <CityPick value={city} currentId={cityId} disabled={saving} onChange={setCity} />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={!valid || saving}>{saving ? text.busy : text.button}</button>
        {onCancel && <button type="button" className="text-button" onClick={onCancel}>Cancel</button>}
      </div>
      {note && <Notice tone={note.tone}>{note.text}</Notice>}
    </form>
  )
}

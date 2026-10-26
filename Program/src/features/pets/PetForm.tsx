import { useState, type FormEvent } from 'react'
import type { PetView } from '../../types'
import { Stepper } from '../../components/NumberFields'
import { MAX_PET_AGE, ageChoice, capital } from './petText'

export interface PetKind { id: string; label: string }
export interface PetChange { name: string; looks?: string; kind: string; age?: number }

interface Props {
  /** Unique per form on the page: the fields' ids start with it. */
  id: string
  kinds: PetKind[]
  /** The pet being changed; left out when adding one. */
  pet?: PetView
  /** Saves the change; true when it was saved, so the form can close. */
  onSave: (change: PetChange) => Promise<boolean>
  onDone: () => void
}

/** Changing a pet, or adding one (`pet` left out): its kind, name, looks and age. Anything left as it was the pet
 * keeps; when adding, the app picks an age that fits the looks. */
export function PetForm({ id, kinds, pet, onSave, onDone }: Props) {
  const [values, setValues] = useState(() => startOf(pet, kinds))
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const change = changeOf(values, pet)
    if (change && await onSave(change)) onDone()
  }
  return (
    <form className={pet ? 'rename-form' : 'rename-form home-add'} onSubmit={(event) => void save(event)}>
      <PetFields id={id} kinds={kinds} pet={pet} values={values} set={(change) => setValues((current) => ({ ...current, ...change }))} />
      <div className="rename-row">
        <button type="submit" className="button primary">{pet ? 'Save' : 'Add'}</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

interface Values { name: string; looks: string; kind: string; age: number }

function startOf(pet: PetView | undefined, kinds: PetKind[]): Values {
  if (pet) return { name: pet.name, looks: pet.looks, kind: pet.kind, age: -1 }
  return { name: '', looks: '', kind: kinds[0]?.id ?? 'cat', age: -1 }
}

/** What to send: a changed pet keeps the name and looks it had when those are cleared; null when adding with no name. */
function changeOf(values: Values, pet?: PetView): PetChange | null {
  const name = values.name.trim() || pet?.name
  if (!name) return null
  const looks = values.looks.trim()
  return { name, looks: pet && !looks ? undefined : looks, kind: values.kind, age: values.age < 0 ? undefined : values.age }
}

interface FieldsProps { id: string; kinds: PetKind[]; pet?: PetView; values: Values; set: (change: Partial<Values>) => void }

/** Adding asks for the kind first; changing leads with the name (as the companion's own Pets panel always has). */
function PetFields({ id, kinds, pet, values, set }: FieldsProps) {
  const kind = <KindSelect id={`${id}-kind`} kinds={kinds} value={values.kind} onChange={(value) => set({ kind: value })} />
  const adding = !pet
  return <>
    {adding && kind}
    <label htmlFor={`${id}-name`}>Name</label>
    <input id={`${id}-name`} value={values.name} maxLength={80} required={adding} placeholder={adding ? 'Biscuit' : undefined} autoFocus={adding}
      onChange={(event) => set({ name: event.target.value })} />
    <label htmlFor={`${id}-looks`}>Looks</label>
    <input id={`${id}-looks`} value={values.looks} maxLength={300} placeholder={adding ? 'a small orange tabby with a white bib' : undefined}
      onChange={(event) => set({ looks: event.target.value })} />
    {!adding && kind}
    <Stepper label="Age" value={values.age} min={-1} max={MAX_PET_AGE} onChange={(age) => set({ age })}
      format={(years) => ageChoice(years, pet ? `Keep (${pet.age})` : 'Picked for you')}
      hint={values.age < 0 && adding ? 'Leave it and the app picks one that fits their looks.' : undefined} />
  </>
}

function KindSelect({ id, kinds, value, onChange }: { id: string; kinds: PetKind[]; value: string; onChange: (value: string) => void }) {
  return <>
    <label htmlFor={id}>Kind</label>
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
      {kinds.map((kind) => <option key={kind.id} value={kind.id}>{capital(kind.label)}</option>)}
    </select>
  </>
}

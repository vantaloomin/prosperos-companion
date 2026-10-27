import { useQuery } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { api } from '../../api'
import type { Persona, PetsView } from '../../types'
import { MAX_PET_AGE, PET_KINDS, PETS_KEY, ageChoice } from '../pets/petText'
import { Stepper } from '../../components/NumberFields'
import { MAX_PETS, unsetAge, type PetDraft } from './personaPetsText'

/** The user's own pets: only what the user writes, never invented. Once saved they live their lives in the world,
 * and how each is today shows here in plain words. */
export function PersonaPets({ drafts, onChange, persona }: { drafts: PetDraft[]; onChange: (drafts: PetDraft[]) => void; persona?: Persona }) {
  const lives = useQuery({ queryKey: PETS_KEY, queryFn: () => api<PetsView>('/life/pets'), enabled: !!persona?.active, retry: false })
  const status = (name: string) => lives.data?.yours.find((pet) => pet.name.toLowerCase() === name.trim().toLowerCase())?.status
  const set = (index: number, change: Partial<PetDraft>) => onChange(drafts.map((pet, at) => at === index ? { ...pet, ...change } : pet))
  return (
    <fieldset className="persona-pets">
      <legend>Your pets</legend>
      <p className="subtle">Optional. Pets you add here have lives of their own: off days, vet visits, growing old. Your companions know them by name. Leave the age and the app picks one that fits their looks.</p>
      {drafts.map((pet, index) => (
        <div className="persona-pet" key={index}>
          <div className="persona-pet-row">
            <div className="field">
              <label htmlFor={`persona-pet-name-${index}`}>Name</label>
              <input autoComplete="off" id={`persona-pet-name-${index}`} value={pet.name} maxLength={40} placeholder="Biscuit" onChange={(event) => set(index, { name: event.target.value })} />
            </div>
            <div className="field">
              <label htmlFor={`persona-pet-kind-${index}`}>Kind</label>
              <select id={`persona-pet-kind-${index}`} value={pet.kind} onChange={(event) => set(index, { kind: event.target.value })}>
                {PET_KINDS.map((kind) => <option key={kind.id} value={kind.id}>{kind.label}</option>)}
              </select>
            </div>
            <Stepper label="Age" value={pet.age} min={-1} max={MAX_PET_AGE} onChange={(age) => set(index, { age })} format={(years) => ageChoice(years, unsetAge(pet))} />
          </div>
          <label htmlFor={`persona-pet-looks-${index}`}>Looks</label>
          <input autoComplete="off" id={`persona-pet-looks-${index}`} value={pet.looks} maxLength={160} placeholder="a one-eyed orange tabby" onChange={(event) => set(index, { looks: event.target.value })} />
          {status(pet.name) && <p className="subtle pet-status">{status(pet.name)}</p>}
          <button type="button" className="text-button" onClick={() => onChange(drafts.filter((_, at) => at !== index))}><X aria-hidden="true" />Remove {pet.name.trim() || 'this pet'}</button>
        </div>
      ))}
      {drafts.length < MAX_PETS && (
        <button type="button" className="button quiet" onClick={() => onChange([...drafts, { name: '', kind: 'cat', looks: '', age: -1 }])}><Plus aria-hidden="true" />Add a pet</button>
      )}
    </fieldset>
  )
}

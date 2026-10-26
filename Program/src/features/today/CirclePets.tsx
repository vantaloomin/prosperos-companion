import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { CirclePerson, CirclePetView } from '../../types'
import { Notice } from '../../components/Feedback'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { PET_KINDS, capital, sentenceOf } from '../pets/petText'
import { PetForm, type PetChange } from '../pets/PetForm'
import type { Act } from './PersonForm'

type Feedback = { tone: 'info' | 'error'; text: string }

/** Someone's pets while their card is open for changes (companion/life/circle_pets.py): the app seeded them, and
 * the user can change, remove or add one. Each change saves on its own; a removed pet stays gone. */
export function CirclePets({ person, act }: { person: CirclePerson; act: Act }) {
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const pets = person.pets ?? []
  const add = (change: PetChange) => act(() => api(`/life/circle/${person.id}/pets`, change), `${change.name} is ${person.name}'s now.`, setFeedback)
  const headingId = `circle-pets-${person.id}`
  return (
    <section className="circle-pets" aria-labelledby={headingId}>
      <h4 id={headingId}>{person.name}'s pets</h4>
      <p className="subtle">Changes here save on their own.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {pets.length === 0 && !adding && <p className="subtle">No pets right now.</p>}
      {pets.length > 0 && <ul className="circle-pet-list">{pets.map((pet) => <PetRow key={pet.key} pet={pet} person={person} act={act} tell={setFeedback} />)}</ul>}
      {adding
        ? <PetForm id={`circle-pet-${person.id}-add`} kinds={PET_KINDS} onSave={add} onDone={() => setAdding(false)} />
        : <button type="button" className="text-button" onClick={() => { setFeedback(null); setAdding(true) }}><Plus aria-hidden="true" />Add a pet</button>}
    </section>
  )
}

function PetRow({ pet, person, act, tell }: { pet: CirclePetView; person: CirclePerson; act: Act; tell: (feedback: Feedback) => void }) {
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)
  const path = `/life/circle/${person.id}/pets/${pet.number}`
  const save = (change: PetChange) => act(() => api(path, change, 'PATCH'), `Saved ${change.name}. Upcoming days use the new details.`, tell)
  const remove = async () => { setRemoving(false); await act(() => api(`${path}/remove`, {}), `${pet.name} is no longer ${person.name}'s.`, tell) }
  const label = PET_KINDS.find((kind) => kind.id === pet.kind)?.label ?? pet.kind_label
  return (
    <li className="circle-pet">
      {editing
        ? <PetForm id={`circle-pet-${person.id}-${pet.number}`} kinds={PET_KINDS} pet={pet} onSave={save} onDone={() => setEditing(false)} />
        : <>
          <p><strong>{pet.name}</strong> <span className="subtle">· {capital(label)}</span></p>
          <p className="subtle">{sentenceOf(`${pet.looks}, ${pet.age}`)}</p>
          <div className="person-actions">
            <button type="button" className="text-button" aria-label={`Edit ${pet.name}`} onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Edit</button>
            <button type="button" className="text-button" aria-label={`Remove ${pet.name}`} onClick={() => setRemoving(true)}><Trash2 aria-hidden="true" />Remove</button>
          </div>
        </>}
      {removing && (
        <ConfirmDialog title={`Remove ${pet.name}?`} onClose={() => setRemoving(false)} actions={<>
          <button type="button" className="button" onClick={() => setRemoving(false)}>Cancel</button>
          <button type="button" className="button primary" onClick={() => void remove()}>Remove</button>
        </>}>
          <p>{pet.name} is no longer {person.name}'s, and the app won't bring them back. You can add a pet for {person.name} yourself.</p>
        </ConfirmDialog>
      )}
    </li>
  )
}

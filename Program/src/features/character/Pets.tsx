import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { CompanionPet, PetsView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PETS_KEY, capital, petDate, petNumbers, sentenceOf } from '../pets/petText'
import { PetForm, type PetChange } from '../pets/PetForm'
import { panelTitle } from './panelText'

type Act = (action: () => Promise<PetsView>, done: string) => Promise<boolean>

/** The companion's pets with lives of their own (companion/life/pets.py): how each is today in plain words, what
 * happened lately, and the ones they have lost. The app decides; the user can rename, redescribe, add or remove. */
export function Pets({ name }: { name: string }) {
  const client = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const pets = useQuery({ queryKey: PETS_KEY, queryFn: () => api<PetsView>('/life/pets') })
  const act: Act = async (action, done) => {
    try {
      client.setQueryData(PETS_KEY, await action())
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    } finally {
      void client.invalidateQueries({ queryKey: ['home'] })
    }
  }
  return (
    <section className="home-panel pets-panel" aria-labelledby="pets-heading">
      <h2 id="pets-heading">{panelTitle(name, 'pets')}</h2>
      <p className="subtle">Pets have lives of their own: off days, vet visits and growing old. How often depends on Settings &gt; Realism.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {pets.isPending && <Loading label="Loading their pets" />}
      {pets.isError && <ErrorNotice error={pets.error} />}
      {pets.isSuccess && <>
        {pets.data.pets.length === 0
          ? <p>{name} has no pets right now.</p>
          : <ul className="person-list">{pets.data.pets.map((pet) => <PetCard key={pet.id} pet={pet} view={pets.data} act={act} />)}</ul>}
        {adding
          ? <AddForm view={pets.data} act={act} onDone={() => setAdding(false)} />
          : <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a pet</button>}
        {pets.data.remembered.length > 0 && (
          <div className="pets-remembered">
            <h3>Remembered</h3>
            <ul className="person-list">{pets.data.remembered.map((pet) => <PetCard key={pet.id} pet={pet} view={pets.data} act={act} gone />)}</ul>
          </div>
        )}
      </>}
    </section>
  )
}

function PetCard({ pet, view, act, gone = false }: { pet: CompanionPet; view: PetsView; act: Act; gone?: boolean }) {
  const [editing, setEditing] = useState(false)
  const label = view.kinds.find((kind) => kind.id === pet.kind)?.label ?? pet.kind_label
  return (
    <li className={`person-card pet-card${gone ? ' removed' : ''}`}>
      <header>
        <p className="subtle">{capital(label)}</p>
        <h3>{pet.name}</h3>
      </header>
      {pet.status && <p className={`pet-status pet-status-${pet.serious ? 'serious' : pet.state}`}>{pet.status}</p>}
      <p>{sentenceOf(`${pet.looks}, ${pet.age}`)}</p>
      {petNumbers(pet) && <p className="subtle pet-numbers">{petNumbers(pet)}</p>}
      {pet.recent.length > 0 && (
        <dl className="pet-recent">{pet.recent.slice(0, 3).map((event) => (
          <div key={`${event.date}-${event.kind}`}><dt><time dateTime={event.date}>{petDate(event.date)}</time></dt><dd>{sentenceOf(event.text)}</dd></div>
        ))}</dl>
      )}
      {editing
        ? <EditForm pet={pet} view={view} act={act} onDone={() => setEditing(false)} />
        : <PetActions pet={pet} act={act} gone={gone} onEdit={() => setEditing(true)} />}
    </li>
  )
}

function PetActions({ pet, act, gone, onEdit }: { pet: CompanionPet; act: Act; gone: boolean; onEdit: () => void }) {
  const remove = () => act(() => api(`/life/pets/${pet.id}/remove`, {}), `${pet.name} is no longer theirs.`)
  const restore = () => act(() => api(`/life/pets/${pet.id}/restore`, {}), `${pet.name} is back, and will stay.`)
  if (gone) return <div className="person-actions"><button type="button" className="text-button" onClick={() => void restore()}><RotateCcw aria-hidden="true" />Bring back</button></div>
  return (
    <div className="person-actions">
      <button type="button" className="text-button" onClick={onEdit}><Pencil aria-hidden="true" />Edit</button>
      <button type="button" className="text-button" onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>
    </div>
  )
}

function EditForm({ pet, view, act, onDone }: { pet: CompanionPet; view: PetsView; act: Act; onDone: () => void }) {
  const save = (change: PetChange) => act(() => api(`/life/pets/${pet.id}`, change, 'PATCH'), 'Saved. Upcoming days use the new details.')
  return <PetForm id={`pet-${pet.id}`} kinds={view.kinds} pet={pet} onSave={save} onDone={onDone} />
}

function AddForm({ view, act, onDone }: { view: PetsView; act: Act; onDone: () => void }) {
  const save = (change: PetChange) => act(() => api('/life/pets', change), `Added ${change.name}.`)
  return <PetForm id="pet-add" kinds={view.kinds} onSave={save} onDone={onDone} />
}

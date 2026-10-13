import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { CompanionPet, PetsView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PETS_KEY, petDate, petNumbers, sentenceOf } from '../pets/petText'

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
      <h2 id="pets-heading">{name}'s pets</h2>
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
      {pet.status && <p className={`pet-status pet-status-${pet.state}`}>{pet.status}</p>}
      <p>{sentenceOf(`${pet.looks}, ${pet.age}`)}</p>
      {petNumbers(pet) && <p className="subtle pet-numbers">{petNumbers(pet)}</p>}
      {pet.recent.length > 0 && (
        <ul className="diary-list pet-recent">{pet.recent.slice(0, 3).map((event) => (
          <li key={`${event.date}-${event.kind}`}><time dateTime={event.date}>{petDate(event.date)}</time> {sentenceOf(event.text)}</li>
        ))}</ul>
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

function KindSelect({ id, view, value, onChange }: { id: string; view: PetsView; value: string; onChange: (value: string) => void }) {
  return <>
    <label htmlFor={id}>Kind</label>
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
      {view.kinds.map((kind) => <option key={kind.id} value={kind.id}>{capital(kind.label)}</option>)}
    </select>
  </>
}

function EditForm({ pet, view, act, onDone }: { pet: CompanionPet; view: PetsView; act: Act; onDone: () => void }) {
  const [name, setName] = useState(pet.name)
  const [looks, setLooks] = useState(pet.looks)
  const [kind, setKind] = useState(pet.kind)
  const [age, setAge] = useState('')
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const body = { name: name.trim() || pet.name, looks: looks.trim() || undefined, kind, age: ageOf(age) }
    if (await act(() => api(`/life/pets/${pet.id}`, body, 'PATCH'), 'Saved. Upcoming days use the new details.')) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <label htmlFor={`pet-name-${pet.id}`}>Name</label>
      <input id={`pet-name-${pet.id}`} value={name} maxLength={80} onChange={(event) => setName(event.target.value)} />
      <label htmlFor={`pet-looks-${pet.id}`}>Looks</label>
      <input id={`pet-looks-${pet.id}`} value={looks} maxLength={300} onChange={(event) => setLooks(event.target.value)} />
      <KindSelect id={`pet-kind-${pet.id}`} view={view} value={kind} onChange={setKind} />
      <AgeInput id={`pet-age-${pet.id}`} value={age} onChange={setAge} placeholder={pet.age} />
      <div className="rename-row">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AddForm({ view, act, onDone }: { view: PetsView; act: Act; onDone: () => void }) {
  const [name, setName] = useState('')
  const [looks, setLooks] = useState('')
  const [kind, setKind] = useState(view.kinds[0]?.id ?? 'cat')
  const [age, setAge] = useState('')
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    if (await act(() => api('/life/pets', { name: name.trim(), looks: looks.trim(), kind, age: ageOf(age) }), `Added ${name.trim()}.`)) onDone()
  }
  return (
    <form className="rename-form home-add" onSubmit={(event) => void save(event)}>
      <KindSelect id="pet-add-kind" view={view} value={kind} onChange={setKind} />
      <label htmlFor="pet-add-name">Name</label>
      <input id="pet-add-name" value={name} maxLength={80} required placeholder="Biscuit" onChange={(event) => setName(event.target.value)} />
      <label htmlFor="pet-add-looks">Looks</label>
      <input id="pet-add-looks" value={looks} maxLength={300} placeholder="a small orange tabby with a white bib" onChange={(event) => setLooks(event.target.value)} />
      <AgeInput id="pet-add-age" value={age} onChange={setAge} placeholder="Picked for you" />
      <div className="rename-row">
        <button type="submit" className="button primary">Add</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AgeInput({ id, value, onChange, placeholder }: { id: string; value: string; onChange: (value: string) => void; placeholder: string }) {
  return <>
    <label htmlFor={id}>Age in years</label>
    <input id={id} className="pet-age" type="number" inputMode="numeric" min={0} max={90} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
  </>
}

/** An age the user typed, or undefined to keep the one the pet has (or let the app pick one). */
function ageOf(text: string): number | undefined {
  const years = Math.round(Number(text))
  return text.trim() === '' || !Number.isFinite(years) ? undefined : Math.min(90, Math.max(0, years))
}

function capital(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

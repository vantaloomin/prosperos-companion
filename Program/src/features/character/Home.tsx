import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { HomeItem, HomeKind, HomeView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { KIND_LABELS, homeTitle, itemDetail, rentText, sentence, sinceText } from './homeText'

const HOME_KEY = ['home']
const ADDABLE: HomeKind[] = ['pet', 'plant', 'vehicle', 'favorite']

type Act = (action: () => Promise<HomeView>, done: string) => Promise<boolean>

/** Where the companion lives and what they live with: generated from their city, changing slowly, editable here. */
export function Home({ name }: { name: string }) {
  const client = useQueryClient()
  const [removed, setRemoved] = useState(false)
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const home = useQuery({ queryKey: [...HOME_KEY, removed], queryFn: () => api<HomeView>(`/life/home?include_removed=${removed}`) })
  const act: Act = async (action, done) => {
    try {
      await action()
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    } finally {
      void client.invalidateQueries({ queryKey: HOME_KEY })
    }
  }
  return (
    <section className="home-panel" aria-labelledby="home-heading">
      <h2 id="home-heading">{name}'s home and belongings</h2>
      <p className="subtle">Drawn from their city's housing data and changing slowly over time. Their moments, pictures and replies mention these. Edits apply to upcoming days; what already happened stays.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {home.isPending && <Loading label="Loading their home" />}
      {home.isError && <ErrorNotice error={home.error} />}
      {home.isSuccess && <>
        <ul className="person-list">{home.data.items.map((item) => <ItemCard key={item.id} item={item} view={home.data} act={act} />)}</ul>
        {adding
          ? <AddForm view={home.data} act={act} onDone={() => setAdding(false)} />
          : <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a belonging</button>}
        <Toggle label="Show things they no longer have" checked={removed} onChange={setRemoved} />
        {removed && <ul className="person-list">{home.data.removed.map((item) => <ItemCard key={item.id} item={item} view={home.data} act={act} gone />)}</ul>}
        {home.data.changes.length > 0 && (
          <div className="home-changes">
            <h3>Recent changes</h3>
            <ul className="diary-list">{home.data.changes.map((change) => <li key={`${change.local_date}-${change.kind}`}><time dateTime={change.local_date}>{change.local_date}</time> {sentence(change.text)}</li>)}</ul>
          </div>
        )}
      </>}
    </section>
  )
}

function ItemCard({ item, view, act, gone = false }: { item: HomeItem; view: HomeView; act: Act; gone?: boolean }) {
  const [editing, setEditing] = useState(false)
  return (
    <li className={`person-card${gone ? ' removed' : ''}`}>
      <header>
        <p className="subtle">{KIND_LABELS[item.kind]}</p>
        <h3>{item.kind === 'home' ? homeTitle(item) : capital(item.name)}</h3>
      </header>
      <ItemFacts item={item} />
      {editing
        ? <EditForm item={item} view={view} act={act} onDone={() => setEditing(false)} />
        : <ItemActions item={item} act={act} gone={gone} onEdit={() => setEditing(true)} />}
    </li>
  )
}

function ItemFacts({ item }: { item: HomeItem }) {
  const detail = item.kind === 'home' ? '' : itemDetail(item)
  const features = item.kind === 'home' ? item.features ?? [] : []
  const rent = item.kind === 'home' ? rentText(item) : null
  const since = sinceText(item)
  return <>
    {detail && <p>{detail}</p>}
    {features.length > 0 && <p>With {features.join(' and ')}.</p>}
    {rent && <p className="subtle">{rent}</p>}
    {since && <p className="subtle">{since}</p>}
  </>
}

function ItemActions({ item, act, gone, onEdit }: { item: HomeItem; act: Act; gone: boolean; onEdit: () => void }) {
  const remove = () => act(() => api(`/life/home/items/${item.id}/remove`, {}), `${capital(item.name)} is gone from their upcoming days.`)
  const restore = () => act(() => api(`/life/home/items/${item.id}/restore`, {}), `${capital(item.name)} is back.`)
  if (gone) return <div className="person-actions"><button type="button" className="text-button" onClick={() => void restore()}><RotateCcw aria-hidden="true" />Restore</button></div>
  return (
    <div className="person-actions">
      <button type="button" className="text-button" onClick={onEdit}><Pencil aria-hidden="true" />Edit</button>
      {item.kind !== 'home' && <button type="button" className="text-button" onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>}
    </div>
  )
}

function varieties(view: HomeView, kind: HomeKind): string[] | null {
  return kind === 'pet' ? view.varieties.pet : kind === 'vehicle' ? view.varieties.vehicle : null
}

function EditForm({ item, view, act, onDone }: { item: HomeItem; view: HomeView; act: Act; onDone: () => void }) {
  const [name, setName] = useState(item.name)
  const [description, setDescription] = useState(item.description)
  const [variety, setVariety] = useState(item.variety)
  const options = varieties(view, item.kind)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const body = { name: name.trim() || item.name, description: description.trim() || undefined, variety: options ? variety : undefined }
    if (await act(() => api(`/life/home/items/${item.id}`, body, 'PATCH'), 'Saved. Upcoming days use the new details.')) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <label htmlFor={`home-name-${item.id}`}>Name</label>
      <input id={`home-name-${item.id}`} value={name} maxLength={80} onChange={(event) => setName(event.target.value)} />
      <label htmlFor={`home-description-${item.id}`}>Description</label>
      <input id={`home-description-${item.id}`} value={description} maxLength={300} onChange={(event) => setDescription(event.target.value)} />
      {options && <VarietySelect id={`home-variety-${item.id}`} options={options} value={variety} onChange={setVariety} />}
      <div className="rename-row">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AddForm({ view, act, onDone }: { view: HomeView; act: Act; onDone: () => void }) {
  const [kind, setKind] = useState<HomeKind>('pet')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const options = varieties(view, kind)
  const [variety, setVariety] = useState('')
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    const body = { kind, name: name.trim(), description: description.trim(), variety: options ? (variety || options[0]) : '' }
    if (await act(() => api('/life/home/items', body), `Added ${name.trim()}.`)) onDone()
  }
  return (
    <form className="rename-form home-add" onSubmit={(event) => void save(event)}>
      <label htmlFor="home-add-kind">What to add</label>
      <select id="home-add-kind" value={kind} onChange={(event) => { setKind(event.target.value as HomeKind); setVariety('') }}>
        {ADDABLE.map((option) => <option key={option} value={option}>{KIND_LABELS[option]}</option>)}
      </select>
      {options && <VarietySelect id="home-add-variety" options={options} value={variety || options[0]} onChange={setVariety} />}
      <label htmlFor="home-add-name">Name</label>
      <input id="home-add-name" value={name} maxLength={80} required placeholder={kind === 'pet' ? 'Biscuit' : kind === 'plant' ? 'the fern' : kind === 'vehicle' ? 'the car' : 'a chipped green mug'} onChange={(event) => setName(event.target.value)} />
      <label htmlFor="home-add-description">Description (optional)</label>
      <input id="home-add-description" aria-describedby="home-add-description-hint" value={description} maxLength={300} placeholder="Such as a grey tabby with one white paw" onChange={(event) => setDescription(event.target.value)} />
      <small id="home-add-description-hint" className="subtle">What it looks like. Pictures and replies use it.</small>
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={!name.trim()}>Add</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function VarietySelect({ id, options, value, onChange }: { id: string; options: string[]; value: string; onChange: (value: string) => void }) {
  return <>
    <label htmlFor={id}>Kind</label>
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => <option key={option} value={option}>{option}</option>)}
    </select>
  </>
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

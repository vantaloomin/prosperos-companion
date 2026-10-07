import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Star, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { WardrobeCategory, WardrobeItem, WardrobeView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { sentence } from './homeText'
import { grouped, pieceSince, pieceTitle, wearingText } from './wardrobeText'

const WARDROBE_KEY = ['wardrobe']

type Act = (action: () => Promise<WardrobeView>, done: string) => Promise<boolean>

/** The companion's clothes: sized and styled from their pay, job and personality, changing slowly, editable here. */
export function Wardrobe({ name }: { name: string }) {
  const client = useQueryClient()
  const [removed, setRemoved] = useState(false)
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const wardrobe = useQuery({ queryKey: [...WARDROBE_KEY, removed], queryFn: () => api<WardrobeView>(`/life/wardrobe?include_removed=${removed}`) })
  const act: Act = async (action, done) => {
    try {
      await action()
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    } finally {
      void client.invalidateQueries({ queryKey: WARDROBE_KEY })
    }
  }
  const view = wardrobe.data
  const wearing = view ? wearingText(view.wearing) : null
  return (
    <section className="home-panel wardrobe-panel" aria-labelledby="wardrobe-heading">
      <h2 id="wardrobe-heading">{name}'s wardrobe</h2>
      <p className="subtle">Sized and styled from their pay, job and personality, and changing slowly as they shop and wear things out. Replies and pictures dress them from these. Edits apply to upcoming days.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {wardrobe.isPending && <Loading label="Loading their wardrobe" />}
      {wardrobe.isError && <Notice tone="error">{wardrobe.error.message}</Notice>}
      {view && <>
        <p>{view.profile.summary}</p>
        {wearing && <p className="subtle">{wearing}</p>}
        {grouped(view.items, view.categories).map(([category, pieces]) => (
          <details key={category} className="wardrobe-group">
            <summary>{view.labels[category]} <span className="subtle">({pieces.length})</span></summary>
            <ul className="wardrobe-list">{pieces.map((item) => <Piece key={item.id} item={item} view={view} act={act} />)}</ul>
          </details>
        ))}
        {adding
          ? <AddForm view={view} act={act} onDone={() => setAdding(false)} />
          : <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a piece</button>}
        <Toggle label="Show clothes they no longer have" checked={removed} onChange={setRemoved} />
        {removed && <ul className="wardrobe-list">{view.removed.map((item) => <Piece key={item.id} item={item} view={view} act={act} gone />)}</ul>}
        {view.changes.length > 0 && (
          <div className="home-changes">
            <h3>Recent changes</h3>
            <ul className="diary-list">{view.changes.map((change) => <li key={`${change.local_date}-${change.kind}`}><time dateTime={change.local_date}>{change.local_date}</time> {sentence(change.text)}</li>)}</ul>
          </div>
        )}
      </>}
    </section>
  )
}

function Piece({ item, view, act, gone = false }: { item: WardrobeItem; view: WardrobeView; act: Act; gone?: boolean }) {
  const [editing, setEditing] = useState(false)
  const since = pieceSince(item)
  const remove = () => act(() => api(`/life/wardrobe/items/${item.id}/remove`, {}), `${pieceTitle(item)} is gone from their upcoming days.`)
  const restore = () => act(() => api(`/life/wardrobe/items/${item.id}/restore`, {}), `${pieceTitle(item)} is back.`)
  return (
    <li className={`wardrobe-piece${gone ? ' removed' : ''}`}>
      <span>
        {pieceTitle(item)}
        {item.favorite && <><Star aria-hidden="true" className="wardrobe-star" /><span className="visually-hidden"> (a favourite)</span></>}
        {item.description && <span className="subtle"> {item.description}</span>}
        {since && <span className="subtle"> · {since}</span>}
      </span>
      {editing
        ? <EditForm item={item} view={view} act={act} onDone={() => setEditing(false)} />
        : <span className="person-actions">
          {gone
            ? <button type="button" className="text-button" onClick={() => void restore()}><RotateCcw aria-hidden="true" />Restore</button>
            : <>
              <button type="button" className="text-button" aria-label={`Edit ${item.name}`} onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Edit</button>
              <button type="button" className="text-button" aria-label={`Remove ${item.name}`} onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>
            </>}
        </span>}
    </li>
  )
}

function CategorySelect({ id, view, value, onChange }: { id: string; view: WardrobeView; value: WardrobeCategory; onChange: (value: WardrobeCategory) => void }) {
  return <>
    <label htmlFor={id}>Kind of clothing</label>
    <select id={id} value={value} onChange={(event) => onChange(event.target.value as WardrobeCategory)}>
      {view.categories.map((option) => <option key={option} value={option}>{view.labels[option]}</option>)}
    </select>
  </>
}

function EditForm({ item, view, act, onDone }: { item: WardrobeItem; view: WardrobeView; act: Act; onDone: () => void }) {
  const [name, setName] = useState(item.name)
  const [description, setDescription] = useState(item.description)
  const [category, setCategory] = useState<WardrobeCategory>(item.category)
  const [favorite, setFavorite] = useState(item.favorite)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const body = { name: name.trim() || item.name, description: description.trim(), category, favorite }
    if (await act(() => api(`/life/wardrobe/items/${item.id}`, body, 'PATCH'), 'Saved. Upcoming days use the new details.')) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <label htmlFor={`wardrobe-name-${item.id}`}>Name</label>
      <input id={`wardrobe-name-${item.id}`} value={name} maxLength={120} onChange={(event) => setName(event.target.value)} />
      <label htmlFor={`wardrobe-description-${item.id}`}>Note (optional)</label>
      <input id={`wardrobe-description-${item.id}`} value={description} maxLength={300} onChange={(event) => setDescription(event.target.value)} />
      <CategorySelect id={`wardrobe-category-${item.id}`} view={view} value={category} onChange={setCategory} />
      <Toggle label="A favourite (worn often)" checked={favorite} onChange={setFavorite} />
      <div className="rename-row">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AddForm({ view, act, onDone }: { view: WardrobeView; act: Act; onDone: () => void }) {
  const [category, setCategory] = useState<WardrobeCategory>('top')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [favorite, setFavorite] = useState(false)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    if (await act(() => api('/life/wardrobe/items', { category, name: name.trim(), description: description.trim(), favorite }), `Added ${name.trim()}.`)) onDone()
  }
  return (
    <form className="rename-form home-add" onSubmit={(event) => void save(event)}>
      <CategorySelect id="wardrobe-add-category" view={view} value={category} onChange={setCategory} />
      <label htmlFor="wardrobe-add-name">What it is</label>
      <input id="wardrobe-add-name" aria-describedby="wardrobe-add-name-hint" value={name} maxLength={120} required placeholder="a mustard corduroy jacket" onChange={(event) => setName(event.target.value)} />
      <small id="wardrobe-add-name-hint" className="subtle">Colour and kind, the way you would describe it. Pictures use these words.</small>
      <label htmlFor="wardrobe-add-description">Note (optional)</label>
      <input id="wardrobe-add-description" value={description} maxLength={300} placeholder="A gift from her sister" onChange={(event) => setDescription(event.target.value)} />
      <Toggle label="A favourite (worn often)" checked={favorite} onChange={setFavorite} />
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={!name.trim()}>Add</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
